import curses
import re
import os, sys

from typing import *

global stack, cached, partition_cache, offset, loop_started
stack = []
cached = {}
partition_cache = {}
offset = 0

base = os.path.dirname(os.path.realpath(__file__))

import fterm # hack thing?
import colors
import control
import formatting

import platform
import filecrypt
import build_settings

term = fterm.FTerm(100, 500, skip_key=10, return_key=10)

loop_started = False

def load(file, label=None, absolute_path=False, indentation="    "):
    global stack, cached, loop_started
    if not label:
        label = "init"
    if not absolute_path:
        target = os.path.join(base, file)
    else:
        target = file
    with open(target) as f:
        text = f.read()

    temp = filecrypt.decrypt(text, build_settings.PASSWORD)
    if temp: text = temp


    expression = r"\s?label (.+):\n"
    labels = re.findall(expression, text)
    split = re.split(expression, text)
    split = split[1:]
    split = dict(zip(split[::2], split[1::2]))
    for key in split:
        split[key] = "\n".join([line[len(indentation):] for line in split[key].splitlines()])
    if label not in labels:
        raise ValueError(f"label \"{label}\" not found in file \"{file}\"")
    
    for item in split:
        cached[(target, item)] = split[item]

    #print(target)
    if label != "options":
        stack.insert(0, (target, label, 0))
    if "options" in split:
        stack.insert(0, (target, "options", 0))
    #print(stack)

    if not loop_started:
        while len(stack) > 0:
            process()

def partition(fulltext):
    global stack, cached
    lines = fulltext.splitlines()
    groups = []
    linegroup = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if line == "":
            if linegroup:
                groups.append(linegroup)
                linegroup = []
            i += 1
            continue
        if line[0] == "#":
            i += 1
            continue
        if len(linegroup) == 0:
            if line.startswith("& "):
                linegroup.append("python")
                linegroup.append(line)
            else:
                linegroup.append("script")
                linegroup.append(line)
            i += 1
            continue
        else:
            if linegroup[0] == "python":
                if line.startswith("& "):
                    linegroup.append(line)
                    i += 1
                    continue
                else:
                    groups.append(linegroup)
                    linegroup = []
                    continue
            elif linegroup[0] == "script":
                if not line.startswith("& ") and not line.startswith("menu "):
                    linegroup.append(line)
                    i += 1
                    continue
                else:
                    groups.append(linegroup)
                    linegroup = []
                    continue
    if linegroup:
        groups.append(linegroup)
    return groups
        
def process():
    global stack, cached, offset
    item = stack[0]
    target, label, index = item
    if (target, label) not in cached:
        raise ValueError(f"label \"{label}\" not found in file \"{target}\"")
    text = cached[(target, label)]
    partitions = partition(text)
    # #print(stack)
    # print(index, len(partitions))
    if index >= len(partitions): # we've reached the end
        stack = stack[1:]
        return

    if partitions[index][0] == "python":
        code = [line[2:] for line in partitions[index][1:]]
        _locals = locals()
        stack[0] = (target, label, index + 1)
        exec("\n".join(code), globals()) # lol
        return

    else:
        lines = partitions[index][1:]
        for line in lines:
            screen = curses.initscr()
            term.maxy, term.maxx = screen.getmaxyx()
            curses.endwin()


            exec("term.display(" + line + ")")
            #print(line, stack)
            #print(stack)
            #stack[0] = (target, label, index + 1)
            ...

    stack[0] = (target, label, index + 1)

    # index += 1
    # stack[0 + offset] = (target, label, index)
    # offset = 0


def jump(label):
    global stack, offset
    target, _, _ = stack[0]
    stack.insert(0, (target, label, 0))
    offset += 1
        
def quit(code=0):
    sys.exit(code)

def shutdown():
    if platform.system() == "Windows":
        os.system("shutdown /s /t 0")
    else:
        import dbus
        sys_bus = dbus.SystemBus()
        lg = sys_bus.get_object('org.freedesktop.login1','/org/freedesktop/login1')
        pwr_mgmt =  dbus.Interface(lg,'org.freedesktop.login1.Manager')
        shutdown_method = pwr_mgmt.get_dbus_method("PowerOff")
        shutdown_method(True)

import time
if __name__ == "__main__":
    load("tmp1.txt")
    while len(stack) > 0:
        process()
        #time.sleep(3)