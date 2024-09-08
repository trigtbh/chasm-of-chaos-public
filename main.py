from multiprocessing import freeze_support
if __name__ == '__main__':
    freeze_support() # see: https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Multiprocessing

import random
import os, sys
import colors, formatting, control
import copy
import json
import time
import filecrypt
import build_settings

basepath = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(basepath, "items.json"), encoding='utf-8') as f:
    ITEMS = json.load(f)

global announce_new, win
announce_new = False
win = False

# NOTE: part of original game
def generate_floor_map(seed: int, floor: int):
    # seed: the random seed to use - generated at a later point
    # floor: the floor number

    # this function accomplishes two tasks
    # 1: generate what each room's purpose is (encounter, loot, shop, etc.)
    # 2: generate the map of the floor by connecting rooms together

    floor_map = {
        0: [None, None, None, None] # north, east, south, west
    }

    rooms = {0: "entrance"} # starting room will always be room 0
    
    rgen = random.Random((seed + floor)) # <-- where the magic happens
    # this ensures that the same player will always get the same set of rooms in each floor
    
    togen = []
    for _ in range(10 + floor - 1):
        togen.append("encounter")

    extras = ["loot", "shrine", "cursed"]

    # randomly add extra rooms by setting encounter rooms to the extras
    for i in range(len(togen)):
        if rgen.randint(1, 100) <= 50:
            togen[i] = rgen.choices(extras, weights=[65, 25, 10])[0]
    
    togen += ["shop", "exit", "key"] # guarantee that there will be one shop, one key room, one exit

    rgen.shuffle(togen) # add randomly

    # step 1: attach rooms to each other in a grid-like fashion
    rnum = 0
    for item in togen: # for each room to generate:
        rnum += 1
        rooms[rnum] = item 
        placement = []

        # find each open face throughout the entire map that a new room can be attached to
        for room in range(len(floor_map)):
            for direction in range(len(floor_map[room])):
                if floor_map[room][direction] is None:
                    placement.append((room, direction))

        # randomly select a location to attach it to
        location = rgen.choice(placement)
        floor_map[location[0]][location[1]] = rnum
        opposite = (location[1] + 2) % 4 # find the opposite face
        temp = [None, None, None, None]
        temp[opposite] = location[0] # make the connection the other way as well
        floor_map[rnum] = temp

    # step 2: connect rooms randomly through tunnels
    for room in floor_map: # for each room in the map
        for i in range(len(floor_map[room])): # for each face of the room
            if floor_map[room][i] == None: # if the face is open (doesn't have an attached room)
                for room_2 in floor_map: # for each room in the map (again)
                    if room == room_2: continue # skip if it's the same room
                    if floor_map[room_2][(i + 2) % 4] == None and rgen.random() < 0.15: # if the opposite face of the other room is open and a random number is less than 0.15
                        floor_map[room][i] = -1 * room_2 # connect the rooms
                        floor_map[room_2][(i + 2) % 4] = -1 * room # connect the rooms the other way as well
                        break

    return floor_map, rooms # return generated map and room types

# NOTE: part of original game
def generate_blank_dungeon(seed, name):
    # get wooden sword item
    wooden_sword = None
    for item in ITEMS:
        if item['name'] == "Wooden Sword":
            wooden_sword = item
            break
    assert wooden_sword is not None
    wooden_sword = copy.deepcopy(wooden_sword)
    level = 1
    wooden_sword["level"] = 1
    wooden_sword["attack"] = 5 # let's make it a bit fair

    bought = {}
    # get room data
    _, rooms = generate_floor_map(seed, 1)
    for room in rooms:
        if rooms[room] == "shop":
            bought[str(room)] = []

    return {
        "seed": seed,
        "name": name,
        "floor": 1,
        "room": 0,
        "health": 20,
        "max_health": 20,
        "visited": [],
        "interacted": [],
        "xp": 0,
        "level": 1,
        "effects": [],
        "inventory": [],
        "armor": [None, None, None, None],
        "weapon": wooden_sword,
        "shop_bought": bought,
        "money": 0
    }

def parse_item_description(item):
    parsed = []
    for i, line in enumerate(item["desc"].split("\n")):
        parsed.append(formatting.ITALIC_ON)
        if item["rarity"] == "special" and i > 0:
            parsed.append(colors.MAGENTA)
        parsed.append("\t" + line)
        parsed.append(formatting.ITALIC_OFF)
        if item["rarity"] == "special" and i > 0:
            parsed.append(colors.WHITE)
        parsed.append("\n")
    return tuple(parsed[:-1])
        
def shop(data):
    map_, rooms = generate_floor_map(data["seed"], data["floor"])
    items_to_add = []
    raw_items = []
    rgen = random.Random(data["seed"] + data["floor"] + data["room"])
    rarities = ["common", "rare", "epic"]
    for i in range(rgen.randint(3, 5)):
        rarity = rgen.choices(rarities, weights=[60, 30, 10])[0]
        items = [item for item in ITEMS if item["rarity"] == rarity]
        item = rgen.choice(items)

        if item["type"] == "weapon":
            level = max(1, data["level"] + rgen.randint(-2, 5))
            sword = copy.deepcopy(item)
            sword["name"] = "Level " + str(level) + " " + sword["name"]
            sword["level"] = level
            sword["attack"] = max(1, level * sword["data"]["power"] + rgen.randint(0, int(sword["data"]["power"])))
            sword["cost"] = max(1, level // 2 * (rarities.index(rarity) + 1) * 4 + rgen.randint(0, int(sword["data"]["power"])))
            sword["id"] = hash(json.dumps(sword, sort_keys=True))
            raw_items.append(sword)
        elif item["type"] == "weapon":
            level = max(1, data["level"] + rgen.randint(-2, 5))
            armor = copy.deepcopy(item)
            armor["name"] = "Level " + str(level) + " " + armor["name"]
            armor["level"] = level
            armor["defense"] = max(1, level * armor["data"]["defense"] // 2 + rgen.randint(0, armor["data"]["defense"]))
            armor["cost"] = max(1, level // 2 * (rarities.index(rarity) + 1) * 4 + rgen.randint(0, armor["data"]["defense"]))
            armor["id"] = hash(json.dumps(armor, sort_keys=True))
            raw_items.append(armor)
        else:
            item = copy.deepcopy(item)
            item["cost"] = max(1, (rarities.index(rarity) + 1) * 50 + rgen.randint(-10, 10))
            item["id"] = hash(json.dumps(item, sort_keys=True))
            raw_items.append(item)

    purchased_here = data["shop_bought"][str(data["room"])]

    for item in raw_items:
        if item["id"] not in purchased_here:
            items_to_add.append(item)

    show = False
    while True:
        if show: term.character_delay = 0
        term.clear()
        term.display("A lonely trader offers items for sale.\nYou have ", colors.YELLOW, formatting.BOLD_ON, data["money"], " coins", formatting.BOLD_OFF, colors.WHITE, ".\nUse the menu below to view their wares.")
        options = [item["name"] for item in items_to_add]
        options.append("Exit")
        choice = term.menu(options, [], return_index=True) # had to add return_index into fterm to get the specific index, as different items can have the same name
        show = True
        term.character_delay = 20
        if choice == len(options) - 1:
            break

        item = items_to_add[choice]
        term.display(*parse_item_description(item))
        term.display("\nCost: ", formatting.BOLD_ON, colors.YELLOW, item["cost"], " coins", formatting.BOLD_OFF, colors.WHITE, "\n")
        if data["money"] < item["cost"]:
            term.display("You do not have enough coins to purchase this item.")
            term.input("Press ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
            continue
        else:
            term.display("Would you like to purchase this item?")
            yn = term.menu(["Yes", "No"], [])
            if yn == "Yes":
                data["money"] -= item["cost"]
                data["shop_bought"][str(data["room"])].append(choice)
                data["inventory"].append(item)
                items_to_add.remove(item)
                term.display("You purchased the ", item["name"], " for ", formatting.BOLD_ON, colors.YELLOW, item["cost"], " coins", formatting.BOLD_OFF, colors.WHITE, ".")
                term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
                data["shop_bought"][str(data["room"])].append(item["id"])

def process_potion(data, item):
    if "Powerup" in item["name"]:
        data["effects"].append({"name": "powerup", "duration": item["data"]["duration"], "power": item["data"]["power"]})
    if "Precision" in item["name"]:
        data["effects"].append({"name": "precision", "duration": item["data"]["duration"], "power": item["data"]["power"]})
    if "Regeneration" in item["name"]:
        data["effects"].append({"name": "regeneration", "duration": item["data"]["duration"], "power": item["data"]["power"]})
    if "Health" in item["data"]:
        data["health"] += item["data"]["power"]
        data["health"] = min(data["health"], data["max_health"])
    if "Hardening" in item["name"]:
        data["effects"].append({"name": "hardening", "duration": item["data"]["duration"], "power": item["data"]["power"]})
    if "Evasion" in item["name"]:
        data["effects"].append({"name": "evasion", "duration": item["data"]["duration"], "power": item["data"]["power"]})

def encounter(data, cursed):
    enemies = ["Skeleton", "Orc", "Spider", "Ghoul", "Troll", "Bandit", "Mummy", "Werewolf", "Dark Wizard", "Necromancer", "Minotaur", "Lich", "Gargoyle", "Demon", "Dragon"]
    level = data['level']
    floor = data['floor']

    if level < 5:
        enemy = random.choice(enemies[:5])
    elif level < 10:
        enemy = random.choice(enemies[:10])
    else:
        enemy = random.choice(enemies)

    enemy_level = max(1, level + random.randint(-2, 2))
    if cursed:
        enemy_level += random.randint(1, 10)
    enemy_health = 15 + (level * 2) + (floor * 2) + random.randint(-5, 5) + (enemy_level // 2)
    enemy_damage = max(1, enemy_level + (floor // 2) + random.randint(-2, 2))
    
    term.display("\nYou encounter a ", formatting.BOLD_ON, (colors.RED if cursed else colors.WHITE), "Level " + str(level) + " ", ("Cursed " if cursed else ""), enemy, formatting.BOLD_OFF, colors.WHITE, "!\n")
    term.input("Press ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to begin the battle.")
    
    defense_chance = 40
    dc = defense_chance
    hit_chance = 70
    flee_chance = 35
    if cursed:
        defense_chance = 20
        hit_chance = 50

    protect_defense = False

    active = []

    show = False
    while data["health"] > 0 and enemy_health > 0:
        
        term.clear()
        if show: term.character_delay = 0
        term.display("Enemy: ", formatting.BOLD_ON, (colors.RED if cursed else colors.WHITE), "Level " + str(level) + " ", ("Cursed " if cursed else ""), enemy, formatting.BOLD_OFF, colors.WHITE)
        term.display("Enemy Health: ", formatting.BOLD_ON, (colors.RED if cursed else colors.WHITE), str(enemy_health), " HP", formatting.BOLD_OFF, colors.WHITE)
        term.display("\nYour Health: ", formatting.BOLD_ON, colors.GREEN, data["health"], " HP", formatting.BOLD_OFF, colors.WHITE)
        term.display("Current Weapon: ", formatting.BOLD_ON, colors.YELLOW, data["weapon"]["name"], " - ", str(data["weapon"]["attack"]) + " Attack\n", formatting.BOLD_OFF, colors.WHITE)
        term.display("What would you like to do?")
        options = ["Attack", "Defend", "Inventory", "Flee"]
        choice = term.menu(options, [], unselected_color=(colors.CYAN, formatting.BOLD_ON))

        term.character_delay = 20
        if not show: show = True

        if choice == "Attack":
            attack_strength = data['weapon']['attack']
            hit_chance_ = hit_chance
            for effect in data['effects']:
                if effect['name'] == "powerup":
                    attack_strength *= (1 + (effect['power'] / 100))
                if effect['name'] == "powerdown":
                    attack_strength *= (1 - (effect['power'] / 100))
                if effect['name'] == "precision":
                    hit_chance_ *= (1 + (effect['power'] / 100))

            incr = 0
            for item in data["armor"]:
                if item is None: continue
                if "Iron" in item["name"]:
                    incr += 10
                elif "Dragon Scale" in item["name"]:
                    incr += 12.5

            attack_strength *= (1 + (incr / 100))
            attack_strength = int(round(attack_strength))

            if random.randint(1, 100) <= hit_chance_:
                todisplay = min(attack_strength, enemy_health)
                enemy_health -= attack_strength
                term.display("You hit the ", enemy, " for ", formatting.BOLD_ON, colors.RED, todisplay, " HP", formatting.BOLD_OFF, colors.WHITE, "!") # BUG HERE
                if enemy_health <= 0:
                    term.display("You defeat the ", enemy, "!")
                    xp = 5 + (enemy_level * 2 * random.randint(3, 7)) + (25 if cursed else 0)
                    data["xp"] += xp
                    x = 3 + (enemy_level * 2) + random.randint(0, 25) + (25 if cursed else 0)
                    data["money"] += x
                    term.display("\nYou gain ", formatting.BOLD_ON, colors.GREEN, xp, " XP", formatting.BOLD_OFF, colors.WHITE, " and ", formatting.BOLD_ON, colors.YELLOW, x, " coin" + ("s" if x != 1 else ""), formatting.BOLD_OFF, colors.WHITE, "!")
                    level_req = get_level_requirement(data)
                    while data['xp'] >= level_req:
                        data["xp"] -= level_req
                        data["level"] += 1
                        data["max_health"] += 10
                        data["health"] += 10
                    term.display(formatting.BOLD_ON, colors.GREEN, "LEVEL UP! ", formatting.BOLD_OFF, colors.WHITE, "You are now ", formatting.BOLD_ON, colors.GREEN, "Level " + str(data['level']), formatting.BOLD_OFF, colors.WHITE, "!")
                    term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue your journey.")
                    return True
                else:
                    term.display("The ", enemy, " has ", formatting.BOLD_ON, colors.RED, enemy_health, " HP", formatting.BOLD_OFF, colors.WHITE, " left.")
            else:
                term.display("You miss your attack!")
        elif choice == "Defend":
            term.display("You decide to stand your ground!\nYour defense increases.")
            defense_chance += 25
            protect_defense = True
        elif choice == "Inventory":
            term.display("Select an option below.")
            options = data["inventory"]
            options.append("Cancel")
            choice = term.menu(options, [], return_index=True)
            if choice == len(options) - 1: continue
            item = data["inventory"][choice]
            if item["type"] == "special" or "passive" in item:
                term.display(formatting.BOLD_ON, colors.RED, "You cannot use this item in battle.", formatting.BOLD_OFF, colors.WHITE)
                term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
                continue
            if item["type"] == "weapon":
                data["weapon"], data["inventory"][choice] = data["inventory"][choice], data["weapon"]
                term.display("You equip the ", formatting.BOLD_ON, data["weapon"]["name"], formatting.BOLD_OFF, ".")
            elif item["type"] == "armor":
                piece_map = ["Helmet", "Chestplate", "Leggings", "Boots"]
                for i, piece in enumerate(piece_map):
                    if piece in item["name"]:
                        data["armor"][i], data["inventory"][choice] = data["inventory"][choice], data["armor"][i]
                        term.display("You equip the ", formatting.BOLD_ON, data["armor"][i]["name"], formatting.BOLD_OFF, " as your ", piece.lower(), ".")
                        break
            elif item["type"] in ["consumable", "item"]:
                # remove item from inventory
                del data["inventory"][choice]
                if item["type"] == "consumable":
                    if "Potion" in item["name"]:
                        process_potion(data, item)
                
                        term.display("You drink the ", formatting.BOLD_ON, item["name"], formatting.BOLD_OFF, ".")

                elif item["type"] == "item":
                    if item["name"] == "Smoke Bomb":
                        active.append({"name": "smokebomb", "duration": item["data"]["duration"] + 1, "power": item["data"]["power"]})
                    if item["name"] == "Bandages":
                        data["health"] += item["data"]["heal"]
                        data["health"] = min(data["health"], data["max_health"])

                    term.display("You use the ", formatting.BOLD_ON, item["name"], formatting.BOLD_OFF, ".")
                
            data["inventory"] = [x for x in data["inventory"] if x is not None]
        elif choice == "Flee":
            for item in active:
                if item['name'] == "smokebomb": # detect if smokebomb is active
                    flee_chance += item['power']
            
            for effect in data['effects']:
                if effect['name'] == "flee":
                    flee_chance += effect['power']

            for item in data["armor"]:
                if item is None: continue
                if "Obsidian" in item["name"]:
                    flee_chance += 5
                if "Dragon Scale" in item["name"]:
                    flee_chance += 7.5

            if random.randint(1, 100) <= flee_chance:
                term.display("You successfully flee from the ", enemy, "!")
                term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue your journey.")
                return True
            else:
                term.display("You try to escape, but the ", enemy, " blocks your path!")

        # enemy turn
        tempitems = []
        for item in active:
            item["duration"] -= 1
            if item["duration"] > 0:
                tempitems.append(item)
        active = tempitems
        term.display("\nThe ", enemy, " decides what to do", control.CharacterDelay(750), "...")
        term.display("The ", enemy, " attacks!")
        damage = enemy_damage
        for effect in data["effects"]:
            if effect["name"] == "hardening":
                damage *= (1 - (effect["power"] / 100))
        for item in data["armor"]:
            if item is None: continue
            damage -= item["defense"]

        damage = max(0, damage)
        if random.randint(1, 100) <= defense_chance:
            term.display("You successfully defend yourself!")
        else:
            term.display("The ", enemy, " hits you for ", formatting.BOLD_ON, colors.RED, damage, " HP", formatting.BOLD_OFF, colors.WHITE, "!")
            data["health"] -= damage
            data["health"] = max(0, data["health"])
            term.display("You have ", formatting.BOLD_ON, colors.GREEN, data["health"], " HP", formatting.BOLD_OFF, colors.WHITE, " left.")
            if data["health"] <= 0:
                term.display("You died!", control.Delay(3000))
                return False
        if protect_defense:
            protect_defense = False
            defense_chance = dc
        term.display(control.Delay(3000))

def save(data):
    string_data = json.dumps(data)
    encrypted = filecrypt.encrypt(string_data, build_settings.PASSWORD)
    with open(os.path.join(basepath, "save.dat"), "w") as f:
        f.write(encrypted)

def process_effects(data):
    blank = []
    for effect in data["effects"]:
        if effect["name"] == "regeneration":
            data["health"] += (effect["power"] / 100) * data["max_health"] # restores x% of maximum health - very useful!
            data["health"] = min(data["health"], data["max_health"])
        elif effect["name"] == "poison":
            data["health"] -= (effect["power"] / 100) * data["max_health"] # deals x% of maximum health as damage
            data["health"] = max(0, data["health"])
            if data["health"] == 0:
                return False
        effect["duration"] -= 1
        blank.append(effect)
    data["effects"] = blank

    data["health"] += 4 # passive regeneration
    data["health"] = min(data["health"], data["max_health"])

    return True

def move(data, direction):
    mapped = ["North", "East", "South", "West"]
    map_, rooms = generate_floor_map(data["seed"], data["floor"])
    connections = map_[data['room']]
    new_room = abs(connections[direction])
    
    data['room'] = new_room
    term.display("You decide to move ", formatting.BOLD_ON, colors.YELLOW, mapped[direction], formatting.BOLD_OFF, colors.WHITE, control.CharacterDelay(750), "...")

    good = process_effects(data)
    if not good: 
        term.display("You succumb to the poison...", control.Delay(3000))
        return False

    room = rooms[new_room]
    if room == 'encounter' or room == 'cursed':
        if random.random() < (0.9 if room == 'cursed' else 0.5):
            go_ahead = encounter(data, room == "cursed")
            if not go_ahead:
                return False
            
    save(data) # lost too much because of this...
    return True

def get_level_requirement(data):
    a = 5
    b = 2
    c = 25
    x = data["level"]
    return a * (x ** 2) + b * x + c

def character_info(data):
    choice = 0
    categories = ["Overview", "Armor", "Weapon", "Effects", "Exit"]
    show = False
    while categories[choice] != categories[-1]:
        term.clear()
        if show: term.character_delay = 0
        term.display("Use the menu below to view different stats about your character.")
        if not show: show = True
        choice = categories.index(term.menu(categories, []))
        term.character_delay = 20
        if categories[choice] == categories[-1]: break
        if choice == 0:
            term.display("Overview:")
            term.display("\t- Name: ", formatting.BOLD_ON, data["name"], formatting.BOLD_OFF) # does this work???
            term.display("\t- Level: ", colors.BLUE, formatting.BOLD_ON, data["level"], colors.WHITE, formatting.BOLD_OFF)
            term.display("\t- XP: ", colors.BLUE, formatting.BOLD_ON, data["xp"], "/", get_level_requirement(data), colors.WHITE, formatting.BOLD_OFF)
            term.display("\t- HP: ", colors.GREEN, formatting.BOLD_ON, data["health"], "/", data["max_health"], colors.WHITE, formatting.BOLD_OFF)
            term.display("\t- Location: ", colors.YELLOW, formatting.BOLD_ON, "Floor " + str(data["floor"]) + ", Room " + str(data["room"] + 1), colors.WHITE, formatting.BOLD_OFF)
        elif choice == 1:
            term.display("Armor:")
            for i, piece in enumerate(["Helmet", "Chestplate", "Leggings", "Boots"]):
                if data["armor"][i] is None:
                    term.display("\t", piece, ": ", formatting.ITALIC_ON, "No " + piece.lower() + " equipped", formatting.ITALIC_OFF)
                else:
                    term.display("\t", piece, ": ", data["armor"][i]["name"], " - ", colors.CYAN, data["armor"][i]["defense"], " Defense", colors.WHITE, formatting.BOLD_OFF)
        elif choice == 2:
            term.display("Weapon:")
            description = data["weapon"]["desc"]
            description = "\n\t".join(description.split("\n")).strip()
            term.display("\tWeapon: ", formatting.BOLD_ON, data["weapon"]["name"], formatting.BOLD_OFF)
            term.display("\tDescription:\n\t", formatting.ITALIC_ON, description, formatting.ITALIC_OFF)
            term.display("\tAttack: ", colors.YELLOW, data["weapon"]["attack"],colors.WHITE)
        elif choice == 3:
            term.display("Effects:")
            if len(data["effects"]) == 0:
                term.display(formatting.ITALIC_ON, colors.MAGENTA, "\tYou have no active effects.", formatting.ITALIC_OFF, colors.WHITE)
            else:
                for i, effect in enumerate(data["effects"]):
                    name = effect["name"]
                    if name == "hardening" and effect["power"] < 0:
                        name = "vulnerability"
                    if name == "evasion" and effect["power"] < 0:
                        name = "slowness"
                    term.display("\t", i + 1, ". ", formatting.BOLD_ON, (colors.GREEN if effect["power"] > 0 else colors.RED), name.title(), formatting.BOLD_OFF, colors.WHITE, " - ", colors.CYAN, effect["power"], "%", colors.WHITE, " for ", colors.MAGENTA, effect["duration"], " rooms", colors.WHITE, formatting.BOLD_OFF)

        term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
    return True

def inventory(data):
    show = False
    while True:
        term.clear()
        if show: term.character_delay = 0
        term.display("Use the menu below to manage your inventory.")
    
        options = [item["name"] for item in data["inventory"]]
        options.append("Exit")
        
        show = True
        choice = term.menu(options, [], return_index=True)
        term.character_delay = 20
        if choice == len(options) - 1:
            break
        item = data["inventory"][choice]
        term.display("Name: ", formatting.BOLD_ON, item["name"], formatting.BOLD_OFF)
        rarity_color = {
            "common": colors.WHITE,
            "rare": colors.GREEN,
            "epic": colors.BLUE,
            "special": colors.MAGENTA
        }
        term.display("Rarity: ", formatting.BOLD_ON, rarity_color[item["rarity"]], item["rarity"].title(), formatting.BOLD_OFF, colors.WHITE)
        description = parse_item_description(item)
        term.display("Description:\n", *description)
        if item["rarity"] == "special":
            term.display(formatting.ITALIC_ON, colors.MAGENTA, "\nThis item cannot be used or dropped.", formatting.ITALIC_OFF, colors.WHITE)
            term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
            continue
        if item["name"] == "Dungeon Key":
            term.display(formatting.ITALIC_ON, colors.MAGENTA, "\nThis item cannot be dropped.\nIt can only be used within a room that has a trapdoor to the next floor.", formatting.ITALIC_OFF, colors.WHITE)
            term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
            continue
        term.display("Select an option below.")
        options = ["Use", "Drop", "Cancel"]
        if item["type"] == "passive" or item["name"] in ["Smoke Bomb"]:
            options.remove("Use")
        choice2 = term.menu(options, [])
        if choice2 == "Cancel":
            continue
        if choice2 == "Use":
            if item["type"] == "weapon":
                data["weapon"], data["inventory"][choice] = data["inventory"][choice], data["weapon"]
                term.display("You equip the ", formatting.BOLD_ON, data["weapon"]["name"], formatting.BOLD_OFF, ".")
            elif item["type"] == "armor":
                piece_map = ["Helmet", "Chestplate", "Leggings", "Boots"]
                for i, piece in enumerate(piece_map):
                    if piece in item["name"]:
                        data["armor"][i], data["inventory"][choice] = data["inventory"][choice], data["armor"][i]
                        term.display("You equip the ", formatting.BOLD_ON, data["armor"][i]["name"], formatting.BOLD_OFF, " as your ", piece.lower(), ".")
                        break
            elif item["type"] in ["consumable", "item"]:
                del data["inventory"][choice] # remove item from inventory
                if item["type"] == "consumable":
                    if "Potion" in item["name"]:
                        process_potion(data, item)
                
                        term.display("You drink the ", formatting.BOLD_ON, item["name"], formatting.BOLD_OFF, ".")

                elif item["type"] == "item":
                    if item["name"] == "Bandages":
                        data["health"] += item["data"]["heal"]
                        data["health"] = min(data["health"], data["max_health"])

                    term.display("You use the ", formatting.BOLD_ON, item["name"], formatting.BOLD_OFF, ".")
                
            data["inventory"] = [x for x in data["inventory"] if x is not None]
            term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
        elif choice2 == "Drop":
            term.display("Are you sure you want to drop this item?")
            yn = term.menu(["Yes", "No"], [])
            if yn == "Yes":
                del data["inventory"][choice]
                data["inventory"] = [x for x in data["inventory"] if x is not None]
                term.display("You remove the ", formatting.BOLD_ON, item["name"], formatting.BOLD_OFF, " from your inventory.")
                term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
            else:
                continue

def room_info(data):
    floor_map, rooms = generate_floor_map(data["seed"], data["floor"])
    room_detail = rooms[data["room"]]
    if room_detail == "entrance":
        term.display("Above you is the entrance that you passed.\n", formatting.BOLD_ON, colors.YELLOW, "Light", formatting.BOLD_OFF, colors.WHITE, " shines down onto the ground.")
    if room_detail == "encounter":
        term.display(formatting.ITALIC_ON, "There doesn't seem to be much here...", formatting.ITALIC_OFF)
    elif room_detail == "shrine":
        if data["room"] not in data["interacted"]:
            term.display("A ", formatting.BOLD_ON, colors.ORANGE, "golden shrine ", formatting.BOLD_OFF, colors.WHITE, "appears in the center of the room.\nInteract with this room to worship the shrine and test your fate.")
        else:
            term.display("A ", formatting.BOLD_ON, colors.ORANGE, "golden shrine ", formatting.BOLD_OFF, colors.WHITE, "appears in the center of the room.\nSatisfied, it rests for the next adventurer to worship it.")
    elif room_detail == "cursed":
        term.display(colors.MAGENTA, formatting.BOLD_ON, "Dark rot ", colors.WHITE, formatting.BOLD_OFF, "seeps across the floor.\nThis room is ", formatting.BOLD_ON, colors.MAGENTA, "cursed", formatting.BOLD_OFF, colors.WHITE, ".\nStronger enemies may spawn, and you are likely to receive harmful effects if you stay here.")
    elif room_detail == "loot":
        r = random.Random(data["seed"] + data["floor"] + data["room"])
        container = r.choice(['chest', 'bag', 'satchel'])
        if data["room"] not in data["interacted"]:
            term.display(f"An abandoned {container} sits in the corner of the room.\nInteract with this room to loot its items.")
        else:
            term.display(f"A {container} sits in the corner of the room.\nIts contents have already been looted.")
    elif room_detail == "shop":
        term.display("A trader sits off to the side, willing to sell you items.\nUse the Shop menu to see what they have to offer.")
    elif room_detail == "exit":
        term.display("A trapdoor rests on the ground, leading the way to the next floor.\nIf you have a ", formatting.BOLD_ON, formatting.ITALIC_ON, "Dungeon Key", formatting.BOLD_OFF, formatting.ITALIC_OFF, ", interact with this room to descend to the next floor.")
    elif room_detail == "key":
        if data["room"] not in data["interacted"]:
            term.display("A shiny ", formatting.BOLD_ON, formatting.ITALIC_ON, "Dungeon Key", formatting.BOLD_OFF, formatting.ITALIC_OFF, " lies on the ground.\nInteract with this room to pick it up.")
        else:
            term.display("The outline of a ", formatting.BOLD_ON, "Dungeon Key", formatting.BOLD_OFF, formatting.ITALIC_OFF, " appears on the ground.\nOne was sitting here for a long time...")

    connections = floor_map[data['room']]
    hallways = []
    tunnels = []
    direction_options = []
    mapped = ["North", "East", "South", "West"]
    for i, c in enumerate(connections):
        if c != None: # SyntaxWarning if using "is", as it compares an int with Nonetype
            if c < 0:
                tunnels.append(mapped[i])
                direction_options.append(mapped[i])
            else:
                hallways.append(mapped[i])
                direction_options.append(mapped[i])

    term.display("")
    if hallways:
        if len(hallways) == 1:
            term.display("Hallways lead to your ", formatting.BOLD_ON, colors.YELLOW, hallways[0], formatting.BOLD_OFF, colors.WHITE, ".")
        elif len(hallways) == 2:
            term.display("Hallways lead to your ", formatting.BOLD_ON, colors.YELLOW, hallways[0], " and ", hallways[1], formatting.BOLD_OFF, colors.WHITE, ".")
        else:
            term.display("Hallways lead to your ", formatting.BOLD_ON, colors.YELLOW, ", ".join(hallways[:-1]), " and ", hallways[-1], formatting.BOLD_OFF, colors.WHITE, ".")

    if tunnels:
        if len(tunnels) == 1:
            term.display("Tunnels lead to your ", formatting.BOLD_ON, colors.ORANGE, tunnels[0], formatting.BOLD_OFF, colors.WHITE, ".")
        elif len(tunnels) == 2:
            term.display("Tunnels lead to your ", formatting.BOLD_ON, colors.ORANGE, tunnels[0], " and ", tunnels[1], formatting.BOLD_OFF, colors.WHITE, ".")
        else:
            term.display("Tunnels lead to your ", formatting.BOLD_ON, colors.ORANGE, ", ".join(tunnels[:-1]), " and ", tunnels[-1], formatting.BOLD_OFF, colors.WHITE, ".")

def interact(data):
    global win
    map_, rooms = generate_floor_map(data["seed"], data["floor"])
    room = rooms[data["room"]]
    if room == "key":
        inventory = data["inventory"]
        if len(inventory) >= 10:
            term.display("Your inventory is full! You cannot pick up the key.\nUse the Inventory menu to use or drop items.")
            term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
            return
        key = None
        for item in ITEMS:
            if item["name"] == "Dungeon Key":
                key = item
                break
        assert key is not None
        data["inventory"].append(key)
        data["interacted"].append(data["room"])
        term.display("You pick up the ", formatting.BOLD_ON, formatting.ITALIC_ON, "Dungeon Key", formatting.BOLD_OFF, formatting.ITALIC_OFF, "!")
        term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
    elif room == "exit":
        inventory = data["inventory"]
        if not any(item["name"] == "Dungeon Key" for item in inventory):
            term.display("You need a ", formatting.BOLD_ON, formatting.ITALIC_ON, "Dungeon Key", formatting.BOLD_OFF, formatting.ITALIC_OFF, " to descend to the next floor.")
            term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
            return
        else:
            f = data["floor"] + 1
            nmap_, nrooms = generate_floor_map(data["seed"], f)
            bought = {}
            for room in nrooms:
                if nrooms[room] == "shop":
                    bought[room] = []

            data["floor"] += 1
            data["room"] = 0
            data["interacted"] = []
            data["shop_bought"] = bought
            data["inventory"] = [item for item in data["inventory"] if item["name"] != "Dungeon Key"]

            save(data)
            term.display("You use the ", formatting.BOLD_ON, formatting.ITALIC_ON, "Dungeon Key", formatting.BOLD_OFF, formatting.ITALIC_OFF, " to open the trapdoor", control.CharacterDelay(750), "...")
            good = process_effects(data)
            if not good:
                term.display("You succumb to the poison...", control.Delay(3000))
                return False
    elif room == "loot":
        inventory = data["inventory"]
        if len(inventory) >= 10:
            term.display("Your inventory is full! You cannot loot this room.\nUse the Inventory menu to use or drop items.")
            term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
            return
        else:
            weights = [60, 25, 8, 7]
            data["interacted"].append(data["room"])
            rgen = random.Random(data["seed"] + data["floor"] + data["room"])
            container = rgen.choice(['chest', 'bag', 'satchel'])
            rarity = rgen.choices(["common", "rare", "epic", "special"], weights=weights)[0]
            if rarity != "special":
                item = rgen.choice([item for item in ITEMS if item["rarity"] == rarity])
            else:
                item_names = [item["name"] for item in inventory]
                special_items = [item for item in ITEMS if item["rarity"] == "special" and item["name"] not in item_names]
                item = random.choice(special_items)
                inventory.append(item)
                data["inventory"] = inventory
                term.display("You open the " + container + " and find the ", formatting.BOLD_ON, colors.MAGENTA, item["name"], colors.WHITE, formatting.BOLD_OFF, "!")

                if len(special_items) == 1:
                    term.display(formatting.BOLD_ON, colors.MAGENTA, "YOU WIN!", colors.WHITE, formatting.BOLD_OFF)
                    term.display("You found all 5 special items!")
                    term.display("You have escaped the ", formatting.BOLD_ON, colors.RED, "Chasm of Chaos", formatting.BOLD_OFF, colors.WHITE, "!")
                    win = True
                    return "win"
                term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")
                return
            if item["type"] == "weapon":
                level = max(1, data['level'] + random.randint(-1, 5))
                sword = copy.deepcopy(item)
                sword['name'] = "Level " + str(level) + " " + item['name']
                sword["attack"] = max(1, level * sword["data"]["power"] + random.randint(0, int(sword["data"]["power"])))
                sword["level"] = level
                data["inventory"].append(sword)
                aoran = "an " if sword["name"][0] in "aeiou" else "a "
                if sword["name"][-1] == "s": aoran = ""
                term.display("You open the " + container + " and find ", aoran, formatting.BOLD_ON, sword["name"], formatting.BOLD_OFF, "!")
            elif item["type"] == "armor":
                level = max(1, data['level'] + random.randint(-1, 5))
                armor = copy.deepcopy(item)
                armor['name'] = "Level " + str(level) + " " + item['name']
                armor["defense"] = max(1, level * armor["data"]["defense"] // 2 + random.randint(0, armor["data"]["defense"]))
                armor["level"] = level
                data["inventory"].append(armor)
                aoran = "an " if armor["name"][0] in "aeiou" else "a "
                if armor["name"][-1] == "s": aoran = ""
                term.display("You open the " + container + " and find ", aoran, formatting.BOLD_ON, armor["name"], colors.WHITE, "!")
            else:
                data["inventory"].append(item)
                aoran = "an " if item["name"][0] in "aeiou" else "a "
                if item["name"][-1] == "s": aoran = ""
                term.display("You open the " + container + " and find ", aoran, formatting.BOLD_ON, item["name"], colors.WHITE, formatting.BOLD_OFF, "!")
            term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")

    elif room == "shrine":
        data["interacted"].append(data["room"])
        term.display("You kneel before the shrine.")
        threshold = 50
        for item in data["inventory"]:
            if item["name"] == "Four-Leaf Clover":
                threshold += 15 
        rgen = random.Random(data["seed"] + data["floor"] + data["room"])
        options = ["health", "attack", "evasion", "defense", "fortune"]
        good = True
        if rgen.random() < 0.5:
            good = False
        choice = rgen.choice(options)

        # massive if/elif tower incoming, prepare :(
        if good:
            term.display("The shrine is ", formatting.BOLD_ON, colors.GREEN, "satisfied", formatting.BOLD_ON, colors.WHITE, ".")
            if choice == "health":
                term.display("You are blessed with ", formatting.BOLD_ON, colors.GREEN, "regeneration", formatting.BOLD_OFF, colors.WHITE, "!")
                data["effects"].append({"name": "regeneration", "power": rgen.choice([10, 20, 30]), "duration": 3})
            elif choice == "attack":
                term.display("You are blessed with ", formatting.BOLD_ON, colors.GREEN, "strength", formatting.BOLD_OFF, colors.WHITE, "!")
                data["effects"].append({"name": "powerup", "power": rgen.choice([10, 20, 30]), "duration": 3})
            elif choice == "evasion":
                term.display("You feel ", formatting.BOLD_ON, colors.GREEN, "boosted", formatting.BOLD_OFF, colors.WHITE, " with the breeze behind you!")
                data["effects"].append({"name": "evasion", "power": rgen.choice([10, 20, 30]), "duration": 3})
            elif choice == "defense":
                term.display("You feel ", formatting.BOLD_ON, colors.GREEN, "protected", formatting.BOLD_OFF, colors.WHITE, "!")
                data["effects"].append({"name": "hardening", "power": rgen.choice([10, 20, 30]), "duration": 3})
            elif choice == "fortune":
                term.display("You are blessed with ", formatting.BOLD_ON, colors.GREEN, "good fortune", formatting.BOLD_OFF, colors.WHITE, "!")
                data["money"] += rgen.randint(10, 150)
        else:
            term.display("The shrine is ", formatting.BOLD_ON, colors.RED, "displeased", formatting.BOLD_OFF, colors.WHITE, " by your presence.")
            if choice == "health":
                term.display("You are cursed with ", formatting.BOLD_ON, colors.RED, "poison", formatting.BOLD_OFF, colors.WHITE, "!")
                data["effects"].append({"name": "poison", "power": -rgen.choice([10, 20, 30]), "duration": 3})
            elif choice == "attack":
                term.display("You are cursed with ", formatting.BOLD_ON, colors.RED, "weakness", formatting.BOLD_OFF, colors.WHITE, "!")
                data["effects"].append({"name": "powerdown", "power": -rgen.choice([10, 20, 30]), "duration": 3})
            elif choice == "evasion":
                term.display("You feel a ", formatting.BOLD_ON, colors.RED, "weight", formatting.BOLD_OFF, colors.WHITE, " drag you down!")
                data["effects"].append({"name": "evasion", "power": -rgen.choice([10, 20, 30]), "duration": 3})
            elif choice == "defense":
                term.display("You feel ", formatting.BOLD_ON, colors.RED, "vulnerable", formatting.BOLD_OFF, colors.WHITE, "!")
                data["effects"].append({"name": "hardening", "power": -rgen.choice([10, 20, 30]), "duration": 3})
            elif choice == "fortune":
                term.display("You are cursed with ", formatting.BOLD_ON, colors.RED, "bad fortune", formatting.BOLD_OFF, colors.WHITE, "!")
                data["money"] -= rgen.randint(10, 150)
                data["money"] = max(0, data["money"])
        term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to continue.")

def main_loop(data):
    global announce_new, win
    show = False

    level_req = get_level_requirement(data)
    while data['xp'] >= level_req:
        data["xp"] -= level_req
        data["level"] += 1
        data["max_health"] += 10
        data["health"] += 10

    while True:
        term.clear()
        term.set_title(f"Chasm of Chaos: Floor {data['floor']}, Room {data['room']}")
        if show: term.character_delay = 0
        if announce_new:
            term.display("You descend to ", formatting.BOLD_ON, "Floor " + str(data["floor"]), formatting.BOLD_OFF, ".")
            announce_new = False
        term.display("You are at ", formatting.BOLD_ON, "Floor " + str(data['floor']) + ", Room " + str(data['room'] + 1), formatting.BOLD_OFF, ".")

        map_, rooms = generate_floor_map(data["seed"], data["floor"])
        connections = map_[data['room']]
        direction_options = []
        mapped = ["North", "East", "South", "West"]
        for i, c in enumerate(connections):
            if c != None: # SyntaxWarning if using "is", as it compares an int with Nonetype
                if c < 0:
                    direction_options.append(mapped[i])
                else:
                    direction_options.append(mapped[i])

        room_info(data)

        term.display("\nSelect an action.")
        options = ["Move", "Inventory", "Character Info"]
        if rooms[data['room']] in ["loot", "shrine", "key", "exit"] and data["room"] not in data["interacted"]:
            options.append("Interact")
        if rooms[data['room']] == "shop":
            options.append("Shop")
        options.append("Quit")
        choice = term.menu(options, [], unselected_color=(colors.CYAN, formatting.BOLD_ON))
        term.character_delay = 20
        goahead = True
        if choice == "Move":
            term.display("What direction would you like to move?")
            direction_choice = term.menu(direction_options, [])
            direction = mapped.index(direction_choice)
            goahead = move(data, direction)
            show = False
        elif choice == "Inventory":
            inventory(data)
            show = True
        elif choice == "Character Info":
            character_info(data)
            show = True
        elif choice == "Interact":
            r = data["room"]
            temp = interact(data)
            if temp == "win": break
            if temp == False: break
            if data["room"] == r:
                show = True
            else:
                announce_new = True
                show = False
        elif choice == "Shop":
            shop(data)
            show = True
        elif choice == "Quit":
            copy = term.character_delay
            term.character_delay = 20
            term.display(colors.RED, formatting.BOLD_ON, "Are you sure you want to quit?", formatting.BOLD_OFF, colors.WHITE)
            yn = ["Yes", "No"].index(term.menu(["Yes", "No"], []))
            if yn == 0:
                save(data)
                sys.exit()
            term.character_delay = copy
            show = True

        if not goahead: break
    term.character_delay = 20
    if win:
        term.clear()
        term.display("After traversing the dungeon for countless hours,\n", formatting.ITALIC_ON, "you", formatting.ITALIC_OFF, ", oh brave ", formatting.BOLD_ON, colors.GREEN, data["name"], formatting.BOLD_OFF, colors.WHITE, ", are the first to escape the ", formatting.BOLD_ON, colors.RED, "Chasm of Chaos", formatting.BOLD_OFF, colors.WHITE, ".", control.Delay(1500))
        term.display("Many will follow in your footsteps, but few will ever achieve your glory.", control.Delay(1500))
        term.display("Congratulations on your victory!", control.Delay(1500), control.CharacterDelay(75), formatting.ITALIC_ON, colors.MAGENTA, "\nWho knows what other adventures await?", formatting.ITALIC_OFF, colors.WHITE, control.Delay(3000), control.CharacterDelay(20))
        term.clear()
        term.display(colors.RED, formatting.BOLD_ON, "Chasm of Chaos", formatting.BOLD_OFF, colors.WHITE, control.Delay(2250))
        term.display("Created by ", formatting.BOLD_ON, colors.CYAN, "Trig", colors.WHITE, formatting.BOLD_OFF, control.Delay(2250))
        term.display("Artwork by ", formatting.BOLD_ON, colors.CYAN, "Beno", colors.WHITE, formatting.BOLD_OFF, control.Delay(2250))
        term.display("\nThank you ", formatting.BOLD_ON, colors.GREEN, "Astro, Duke, Fenris, Flare, and all of 5th period Advanced Software Projects", colors.WHITE, formatting.BOLD_OFF, " for playtesting.\nThis project would not be where it is today without you all.", control.Delay(2250))
        term.display("\nThank you ", formatting.BOLD_ON, colors.BLUE, "Wilson", colors.WHITE, formatting.BOLD_OFF, " for your truly unending support throughout the entire process. :)", control.Delay(2250))
        term.display(control.CharacterDelay(75), "\nAnd finally,", control.Delay(250), " thank ", formatting.BOLD_ON, colors.MAGENTA, "you", control.Delay(500), colors.WHITE, formatting.BOLD_OFF, " for playing!", control.Delay(5000))

        term.input("\nPress ", formatting.BOLD_ON, colors.GREEN, "Enter", formatting.BOLD_OFF, colors.WHITE, " to exit to the main menu.")
        term.clear()
    else:
        term.display(formatting.BOLD_ON, colors.RED, "\nGAME OVER.", formatting.BOLD_OFF, colors.WHITE, control.Delay(3000))
        
        data["floor"] = 1
        data["room"] = 0
        data["interacted"] = []
        data["shop_bought"] = {}
        data["effects"] = []

        map_, rooms = generate_floor_map(data["seed"], data["floor"])
        for room in rooms:
            if rooms[room] == "shop":
                data["shop_bought"][room] = []

        data["health"] = data["max_health"]

        term.display("If you continue from your save, you will be placed at ", formatting.BOLD_ON, "Floor 1, Room 1", formatting.BOLD_OFF, ".")
        term.input(formatting.BOLD_ON, colors.RED, "Press ",  colors.GREEN, "Enter ", colors.RED, "to exit to the main menu.", colors.WHITE, formatting.BOLD_OFF)
    
        save(data)

def main_menu():
    while True:
        term.set_title("Chasm of Chaos")
        global announce_new
        term.character_delay = 20
        term.display("Welcome to the ", colors.RED, formatting.BOLD_ON, control.CharacterDelay(50), "Chasm of Chaos", formatting.BOLD_OFF, colors.WHITE, control.CharacterDelay(20), ".", control.Delay(1000))
        
        term.character_delay = 20
        term.display("Use your arrow keys to move around.")
        term.display("Press ", colors.GREEN, formatting.BOLD_ON, "Enter", formatting.BOLD_OFF, colors.WHITE, " to select.")
        basepath = os.path.dirname(os.path.realpath(__file__))
        os.chdir(basepath)
        options = ["New Game"]
        if os.path.exists("save.dat"):
            options.append("Continue")
        options.append("Quit")
        selection = options.index(term.menu(options, []))
        if selection == 0:
            if os.path.exists(os.path.join(basepath, "save.dat")):
                term.display(colors.CYAN, "You have an existing save file.\nDo you want to overwrite this with a new save?")
                yn = ["Yes", "No"].index(term.menu(["Yes", "No"], []))
                if yn == 1:
                    term.line_enter = True
                    term.display(formatting.BOLD_ON, colors.RED, "Press ",  colors.GREEN, "Enter ", colors.RED, "to exit the game.")
                    sys.exit()
            name = term.input("Enter your ", colors.GREEN, formatting.BOLD_ON, "hero name", formatting.BOLD_OFF, colors.WHITE, ": ")
            seed = time.time()
            data = generate_blank_dungeon(seed, name)

            string_data = json.dumps(data)
            encrypted = filecrypt.encrypt(string_data, build_settings.PASSWORD)
            with open(os.path.join(basepath, "save.dat"), "w") as f:
                f.write(encrypted)
            term.clear()
            term.line_enter = True
            term.display(formatting.ITALIC_ON, colors.CYAN, "Press ", formatting.ITALIC_OFF, formatting.BOLD_ON, colors.GREEN, "Enter ", formatting.BOLD_OFF, formatting.ITALIC_ON, colors.CYAN, "at the end of each line to continue.", colors.WHITE)
            term.display("Welcome to the dungeon, ", formatting.BOLD_ON, colors.CYAN, data["name"], formatting.BOLD_OFF, colors.WHITE, "!")
            term.display("Your objective is to traverse the endless dungeon and find 5 items of extreme value:")
            term.display("- The ", colors.MAGENTA, formatting.BOLD_ON, "Echoing Sphere", colors.WHITE, formatting.BOLD_OFF)
            term.display("- The ", colors.BLUE, formatting.BOLD_ON, "Flickering Light", colors.WHITE, formatting.BOLD_OFF)
            term.display("- The ", colors.CYAN, formatting.BOLD_ON, "Timeless Tear", colors.WHITE, formatting.BOLD_OFF)
            term.display("- The ", colors.YELLOW, formatting.BOLD_ON, "Glowing Thread", colors.WHITE, formatting.BOLD_OFF)
            term.display("- The ", colors.RED, formatting.BOLD_ON, "Eternal Flame", colors.WHITE, formatting.BOLD_OFF)
            term.display("Only then will you be able to escape.")
            term.display("\nYour character has ", formatting.BOLD_ON, colors.GREEN, "20 HP", formatting.BOLD_OFF, colors.WHITE, ".\nIf you run out, it's ", colors.RED, formatting.BOLD_ON, "game over", colors.WHITE, formatting.BOLD_ON, ".")
            term.display("\n", formatting.BOLD_ON, "Press ",  colors.GREEN, "Enter ", colors.WHITE, "to begin your descent into the ", colors.RED, formatting.BOLD_ON, "Chasm of Chaos",  colors.WHITE, ".", formatting.BOLD_OFF)
            term.line_enter = False
            main_loop(data)
        elif selection == 1:
            if options[1] == "Quit":
                sys.exit()
            else:
                with open(os.path.join(basepath, "save.dat")) as f:
                    encrypted = f.read()
                data = filecrypt.decrypt(encrypted, build_settings.PASSWORD)
                if data is None:
                    term.line_enter = True
                    term.display(formatting.BOLD_ON, colors.RED, "Your save data could not be read.\nPress ", colors.GREEN, "Enter ", colors.RED, "to delete your save file and quit the game.")
                    os.remove(os.path.join(basepath, "save.dat"))
                    sys.exit()
                data = json.loads(data)
                main_loop(data)
        else:
            sys.exit()

import fterm
term = fterm.FTerm()
term.line_enter = False
term.line_skip = False

if __name__ == "__main__":
    main_menu()