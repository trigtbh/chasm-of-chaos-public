import curses
import curses.textpad

import colors
import formatting
import control

from typing import *

from tkinter import messagebox

import os, sys
import platform

if platform.system() == "Windows":
    import ctypes

screen = curses.initscr()
screen.keypad(True)

curses.start_color()
curses.use_default_colors()

import signal

def signal_handler(signal, frame):
    sys.exit()

signal.signal(signal.SIGINT, signal_handler)

for color in [colors.BLACK, colors.RED, colors.GREEN, colors.YELLOW, colors.BLUE, colors.MAGENTA, colors.CYAN, colors.WHITE, colors.ORANGE, colors.PURPLE, colors.BROWN, colors.PINK, colors.GRAY]:
    curses.init_pair(color.fg + 5, color.fg, 0)

curses.endwin()

def terminate(x):
    if x == 10:
        return 7
    if x == 3:
        raise KeyboardInterrupt
    return x

class FTerm:
    def __init__(self, rows: int=100, cols: int=500, skip_key: Union[int, List[int]]=10, return_key: Union[int, List[int]]=10):
        curses.noecho()
        screen = curses.initscr()
        self.maxy, self.maxx = screen.getmaxyx()
        curses.endwin()

        self.system = platform.system()

        self.pad = curses.newpad(rows, cols)
        self.pad.scrollok(True)
        self.pad.idlok(True)
        self.pad.nodelay(True)

        curses.raw()

        self.x = 0
        self.y = 0

        self.pad.move(0, 0)

        self.character_delay = 20

        self.skip_key = skip_key
        self.return_key = return_key

        self.line_skip = True
        self.line_enter = True
        self.global_delay = 0

        self.info = messagebox.showinfo
        self.warning = messagebox.showwarning
        self.error = messagebox.showerror
        self.yesno = messagebox.askyesno
        self.question = messagebox.askquestion
        self.okcancel = messagebox.askokcancel


    def input(self, *args, accept_blank=False):
        le = self.line_enter
        self.line_enter = False
        
        self.display(*args, newline=False)
        self.pad.nodelay(False)
        
        padtopleft = (max(0, self.y - self.maxy + 1), 0)
        windowtopleft = (0, 0)
        windowbottomright = (self.maxy - 1, self.maxx - 1)
        
        left_bound = self.x
        curses.noecho()

        self.pad.refresh(*padtopleft, *windowtopleft, *windowbottomright)
        
        window = curses.newwin(1, self.maxx - left_bound, self.y, left_bound)
        window.refresh()
        self.pad.overlay(window)
        tb = curses.textpad.Textbox(window)
        try:
            string = tb.edit(terminate).strip()
        except KeyboardInterrupt:
            if accept_blank:
                string = ""
            else:
                sys.exit()
        window.overwrite(self.pad)

        self.y += 1
        self.x = 0
        self.pad.nodelay(True)
        self.line_enter = le
        return string.strip()

    def menu(self, options: List[str], selected: List[int], return_index=False, multi_select=False, selected_color=(colors.GREEN, formatting.BOLD_ON), unselected_color=(colors.WHITE, formatting.BOLD_OFF), echo=True):
        if multi_select:
            options.append("Confirm")
        window = curses.newwin(len(options), max([len(x) for x in options]) + 3, self.y, 0)
        window.keypad(True)
        window.nodelay(True)
        window.scrollok(True)
        window.idlok(True)
        window.refresh()
        curses.flushinp()

        self.pad.overlay(window)

        # calculate formatting value for selected and unselected
        selected_val = (curses.A_BOLD if selected_color[1].bold == 1 else 0) + (curses.A_UNDERLINE if selected_color[1].underline == 1 else 0) + (curses.A_ITALIC if selected_color[1].italic == 1 else 0)
        unselected_val = (curses.A_BOLD if unselected_color[1].bold == 1 else 0) + (curses.A_UNDERLINE if unselected_color[1].underline == 1 else 0) + (curses.A_ITALIC if unselected_color[1].italic == 1 else 0)
        

        max_width = max([len(x) for x in options])
        for x in range(max_width):
            for y in range(len(options)):
                if len(options[y]) > x:
                    if y in selected:
                        window.addch(y, x + 2, options[y][x], curses.color_pair(selected_color[0].fg + 5) + selected_val)
                    else:
                        window.addch(y, x + 2, options[y][x], curses.color_pair(unselected_color[0].fg + 5) + unselected_val)
                else:
                    pass
            window.refresh()
            curses.napms(self.character_delay)

        

        window.addch(0, 0, ">", curses.color_pair(selected_color[0].fg + 5) + selected_val)
        window.refresh()
        curses.curs_set(0)
        cursor_at = 0

        while True:
            key = window.getch()
            if key == curses.KEY_UP or key == 450:
                window.addch(cursor_at, 0, " ", curses.color_pair(unselected_color[0].fg + 5) + unselected_val)
                cursor_at -= 1
                if cursor_at < 0:
                    cursor_at = len(options) - 1
                window.addch(cursor_at, 0, ">", curses.color_pair(selected_color[0].fg + 5) + selected_val)
                window.refresh()
            elif key == curses.KEY_DOWN or key == 456:
                window.addch(cursor_at, 0, " ", curses.color_pair(unselected_color[0].fg + 5) + unselected_val)
                cursor_at += 1
                if cursor_at >= len(options):
                    cursor_at = 0
                window.addch(cursor_at, 0, ">", curses.color_pair(selected_color[0].fg + 5) + selected_val)
                window.refresh()
            elif key == curses.KEY_ENTER or key in [10, 13]:
                if multi_select:
                    if cursor_at == len(options) - 1:
                        break
                    else:
                        if cursor_at in selected:
                            selected.remove(cursor_at)
                            window.addstr(cursor_at, 2, options[cursor_at], curses.color_pair(unselected_color[0].fg + 5) + unselected_val)
                        else:
                            selected.append(cursor_at)
                            window.addch(cursor_at, 0, ">", curses.color_pair(selected_color[0].fg + 5))
                            window.addstr(cursor_at, 2, options[cursor_at], curses.color_pair(selected_color[0].fg + 5) + selected_val)
                        window.refresh()
                else:
                    break
            elif key == 3:
                sys.exit()
            else:
                window.clear()
                for i in range(len(options)):
                    if i == cursor_at:
                        window.addch(i, 0, ">", curses.color_pair(selected_color[0].fg + 5))
                    if i not in selected:
                        window.addstr(i, 2, options[i], curses.color_pair(unselected_color[0].fg + 5) + unselected_val)
                    else:
                        window.addstr(i, 2, options[i], curses.color_pair(selected_color[0].fg + 5) + selected_val)
                window.refresh()

        window.clear()
        # just write selected options to the window
        if echo:
            if multi_select:
                for i, item in enumerate(sorted(selected)):
                    window.addstr(i, 0, "> " + options[item], curses.color_pair(selected_color[0].fg + 5) + selected_val)
                    self.y += 1
            else:
                window.addstr(0, 0, "> " + options[cursor_at], curses.color_pair(selected_color[0].fg + 5) + selected_val)
                self.y += 1
            window.overwrite(self.pad)
        curses.curs_set(1)
        if multi_select:
            if not return_index:
                c = [options[i] for i in sorted(selected)]
                selected = []
                return c
            else:
                return sorted(selected)
        else:
            if not return_index:
                return options[cursor_at]
            else:
                return cursor_at



    def display(self, *args, newline: bool=True):
        
        
        delay = self.character_delay
        padtopleft = (max(0, self.y - self.maxy + 1), 0)
        windowtopleft = (0, 0)
        windowbottomright = (self.maxy - 1, self.maxx - 1)
        
        self.pad.refresh(*padtopleft, *windowtopleft, *windowbottomright)

        color_index = 0

        bold = 0
        italic = 0
        underline = 0

        dolineskip = False

        for item in args:
            for x in [int, float, bool]:
                if type(item) == x:
                    item = str(item)
                    break
            if type(item) == str:
                for character in item:
                    val = bold + italic + underline
                    if character == "\n":
                        self.y += 1
                        self.x = 0
                    self.pad.addch(self.y, self.x, character, curses.color_pair(color_index) + val)
                    if character != "\n":
                        self.x += 1
                        if self.x >= self.maxx:
                            self.x = 0
                            self.y += 1
                    self.pad.move(self.y, self.x)
                    key = self.pad.getch()
                    if key == 3: sys.exit()
                    if type(self.skip_key) == int:
                        if key == self.skip_key and self.line_skip:
                            dolineskip = True
                    elif type(self.skip_key) == list:
                        if key in self.skip_key and self.line_skip:
                            dolineskip = True
                    if not dolineskip:
                        self.pad.refresh(*padtopleft, *windowtopleft, *windowbottomright)
                        curses.napms(delay)
                    
            elif type(item) == colors.Color:
                color_index = item.fg + 5
                self.pad.attron(curses.color_pair(item.fg + 5))
            elif type(item) == formatting.Format:
                if item.bold == 1:
                    bold = curses.A_BOLD
                elif item.bold == -1:
                    bold = 0
                if item.italic == 1:
                    italic = curses.A_ITALIC
                elif item.italic == -1:
                    italic = 0
                if item.underline == 1:
                    underline = curses.A_UNDERLINE
                elif item.underline == -1:
                    underline = 0
            elif type(item) == control.Delay and not dolineskip:
                curses.napms(item.delay)
            elif type(item) == control.CharacterDelay:
                if not item.delay:
                    delay = self.character_delay
                else:
                    delay = item.delay

        
        if self.line_enter:
            self.pad.refresh(*padtopleft, *windowtopleft, *windowbottomright)
            self.pad.nodelay(False)
            not_valid = True
            while not_valid:
                key = self.pad.getch()
                if key == 3: sys.exit()
                if type(self.return_key) == int:
                    if key == self.return_key:
                        not_valid = False
                elif type(self.return_key) == list:
                    if key in self.return_key:
                        not_valid = False
            self.pad.nodelay(True)
        else:
            self.pad.refresh(*padtopleft, *windowtopleft, *windowbottomright)
            curses.napms(self.global_delay)
        
        if newline:
            self.y += 1
            self.x = 0

    

    def clear(self):
        self.pad.clear()
        self.x = 0
        self.y = 0
        padtopleft = (max(0, self.y - self.maxy + 1), 0)
        windowtopleft = (0, 0)
        windowbottomright = (self.maxy - 1, self.maxx - 1)
        
        self.pad.refresh(*padtopleft, *windowtopleft, *windowbottomright)

    def set_title(self, title):
        if self.system == "Windows":
            ctypes.windll.kernel32.SetConsoleTitleW(title)
        elif self.system == "Linux":
            sys.stdout.write("\x1b]2;{}\x07".format(title))

t = FTerm()
t.line_enter = True
t.display(formatting.BOLD_ON, "bold on ", formatting.BOLD_OFF)
t.display("bold off")