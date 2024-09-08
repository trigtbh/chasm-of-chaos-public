alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/="

import base64, os
import build_settings

def encrypt(string, encryption_key):
    encoded = base64.b64encode(string.encode("utf-8"))
    
    encoded = str(encoded, "utf-8")
    newstr = ""
    index = 0
    for c in encoded:
        ci = alphabet.index(c)
        ki = alphabet.index(encryption_key[index])
        new = (ci + ki) % len(alphabet)
        newstr = newstr + alphabet[new]
        index = (index + 1) % len(encryption_key)
    return newstr

def decrypt(encoded, encryption_key):
    index = 0
    newstr = ""
    for c in encoded:
        ci = alphabet.index(c)
        ki = alphabet.index(encryption_key[index])
        new = ci - ki
        newstr = newstr + alphabet[new]
        index = (index + 1) % len(encryption_key)
    try:
        return str(base64.b64decode(newstr.encode("utf-8")), "utf-8")
    except:
        return None
    
import random

if __name__ == "__main__":

    name_to_save = input("Name to save: ")
    t = ""

    # make a duplicate of the scripts directory
    base_path = os.path.dirname(os.path.realpath(__file__))
    scripts_path = os.path.join(base_path, "scripts")
    scripts_path_copy = os.path.join(base_path, "scripts_copy")
    if not os.path.exists(scripts_path_copy):
        os.makedirs(scripts_path_copy)
        for filename in os.listdir(scripts_path):
            with open(os.path.join(scripts_path, filename), "r") as f:
                with open(os.path.join(scripts_path_copy, filename), "w") as f2:
                    f2.write(f.read())




    # for every file in the scripts directory:
    scripts_path = os.path.join(base_path, "scripts")
    for filename in os.listdir(scripts_path):
        h = ""
        for i in range(16):
            h = h + random.choice("0123456789abcdef")
        for f2 in os.listdir(scripts_path):
            if f2 == filename:
                continue
            with open(os.path.join(scripts_path, f2), "r") as f:
                data = f.read()
            data = data.replace("scripts/" + filename, "scripts/" + h + ".txt")
            with open(os.path.join(scripts_path, f2), "w") as f:
                f.write(data)
        os.rename(os.path.join(scripts_path, filename), os.path.join(scripts_path, h + ".txt"))
        if filename == name_to_save:
            t = h + ".txt"

    for filename in os.listdir(scripts_path):
        with open(os.path.join(scripts_path, filename), "r") as f:
            data = f.read()
        data = encrypt(data, build_settings.PASSWORD)
        with open(os.path.join(scripts_path, filename), "w") as f:
            f.write(data)

    print(name_to_save + " => " + t)