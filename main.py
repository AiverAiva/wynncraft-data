import requests
import os
import datetime
import time
import json

script_path = os.path.dirname(os.path.realpath(__file__))

if not os.path.isdir(os.path.join(script_path, 'datafiles')):
    os.mkdir(os.path.join(script_path, 'datafiles'))
if not os.path.isdir(os.path.join(script_path, 'guilds')):
    os.mkdir(os.path.join(script_path, 'guilds'))

playerdatapath = os.path.join(script_path, 'datafiles', 'playerdata.json')
if not os.path.isfile(playerdatapath):
    with open(playerdatapath, 'w') as f:
        f.write("{}")
with open(playerdatapath, 'r') as f:
    playerdata = json.load(f)

guildsdatapath = os.path.join(script_path, 'datafiles', 'guilds.json')
if not os.path.isfile(guildsdatapath):
    with open(guildsdatapath, 'w') as f:
        f.write("{}")
with open(guildsdatapath, 'r') as f:
    guildsdata = json.load(f)

OnlineServers = requests.get("https://api.wynncraft.com/public_api.php?action=onlinePlayers").json()
guildlist = []

def updateplayer_fdata(name):
    pd = requests.get(f"https://api.wynncraft.com/v2/player/{name}/stats").json()
    try:
        data = pd["data"][0]
    except:
        return

    player_fdata = { 
        "lastUpdate": round(time.time()),
        "username": data["username"],
        # "server": data["meta"]["location"]["server"],
        "rank": data["meta"]["tag"]["value"],
        "veteran": data["meta"]["veteran"],
        "playtime": round((int(data["meta"]["playtime"])*4.7)/60),
        # "blocksWalked": data["global"]["blocksWalked"],
        # "totalLevel": data["global"]["totalLevel"]["combined"],
        # "questsCompleted": 0,
        # "raidsCompleted": 0,
        # "dungeonsCompleted": 0,
        "stats": {
            # "mobsKilled": 0,
            # "blocksWalked": 0,
            # "logins": 0,
            # "deaths": 0
        },
        "classes": {}
    }
    if data["guild"]["name"]:
        player_fdata["guild"] = {"name": data["guild"]["name"],"rank": data["guild"]["rank"]}
        guildsdata[data["guild"]["name"]] = {"name": data["guild"]["name"]}
        guildlist.append(data["guild"]["name"])
    # print(data["username"])
    for character in data["characters"]:
        cdata = data["characters"][character]
        # player_fdata["questsCompleted"] += cdata["quests"]["completed"]
        # player_fdata["raidsCompleted"] += cdata["raids"]["completed"]
        # player_fdata["dungeonsCompleted"] += cdata["dungeons"]["completed"]
        # player_fdata["classes"][character] = {"type": cdata["type"], "combatLevel": cdata["professions"]["combat"]["level"], "blocksWalked": cdata["blocksWalked"], "playtime": cdata["playtime"]}
        # print(player_fdata["classes"][character])
        for dungeon in cdata["dungeons"]["list"]:
            try:
                player_fdata["stats"][dungeon["name"]] += dungeon["completed"]
            except:
                player_fdata["stats"][dungeon["name"]] = dungeon["completed"]
        for raid in cdata["raids"]["list"]:
            try:
                player_fdata["stats"][raid["name"]] += raid["completed"]
            except:
                player_fdata["stats"][raid["name"]] = raid["completed"]
        # player_fdata["stats"]["mobsKilled"] += data["characters"][character]["mobsKilled"]
        # player_fdata["stats"]["mobsKilled"] += data["characters"][character]["blocksWalked"]
        # player_fdata["stats"]["mobsKilled"] += data["characters"][character]["logins"]
        # player_fdata["stats"]["mobsKilled"] += data["characters"][character]["deaths"]
    playerdata[name] = player_fdata
    time.sleep(0.05)

for server in OnlineServers:
    for player in OnlineServers[server]:
        updateplayer_fdata(player)
    with open(playerdatapath, 'w') as f:
        json.dump(playerdata, f)
    with open(guildsdatapath, 'w') as f:
        json.dump(guildsdata, f)

guilds = list( dict.fromkeys(guildlist))

def getplayer_fdata(member):
    player_fdata = {"rank": member["rank"], "contributed": member["contributed"]}
    try:
        david = requests.get(f"https://api.wynncraft.com/v2/player/{member['name']}/stats").json()
        element = datetime.datetime.strptime(david["data"][0]["meta"]["lastJoin"],"%Y-%m-%dT%H:%M:%S.%fZ")
        player_fdata["lastSeen"] = round(element.timestamp())+8*3600
    except:
        player_fdata["lastSeen"] = 0
    time.sleep(0.1)
    return player_fdata

for guild in guilds:
    path = os.path.join(script_path, 'guilds', guild + '.json')
    if not os.path.isfile(path):
        gd = requests.get(f"https://api.wynncraft.com/public_api.php?action=guildStats&command={guild}").json()
        with open(path, 'w') as f:
            guild_data_e = {"lastUpdate": round(time.time()), "members": {}, "joined": {}, "left": {}}
            try:
                gd["members"]
            except:
                continue
            for member in gd["members"]:
                guild_data_e["members"][member["name"]] = getplayer_fdata(member)
            json.dump(guild_data_e, f)
    with open(path, 'r') as f:
        try:
            guild_data_s=json.load(f)
        except:
            print(guild)
            gd = requests.get(f"https://api.wynncraft.com/public_api.php?action=guildStats&command={guild}").json()
            with open(path, 'w') as f:
                guild_data_e = {"lastUpdate": round(time.time()), "members": {}, "joined": {}, "left": {}}
                try:
                    gd["members"]
                except:
                    continue
                for member in gd["members"]:
                    guild_data_e["members"][member["name"]] = getplayer_fdata(member)
                json.dump(guild_data_e, f)

    try:
        if round(time.time())-guild_data_s["lastUpdate"]<1200: 
            continue
    except:
        pass    

    gd = requests.get(f"https://api.wynncraft.com/public_api.php?action=guildStats&command={guild}").json()
    guild_data_e = {}
    gmlist = []
    leftlist = []
    onlinemembers = []

    for key, value in guild_data_s.items():
        guild_data_e[key] = value

    guild_data_e["lastUpdate"] = round(time.time())

    try:
        gd["members"]
    except:
        continue

    for member in gd["members"]:
        gmlist.append(member["name"])
        if member["name"] not in guild_data_s["members"]: 
            guild_data_e["members"][member["name"]] = getplayer_fdata(member)
            guild_data_e["joined"][member["name"]] = round(time.time())

    for member in guild_data_s["members"]:
        if member not in gmlist:
            guild_data_e["left"][member] = {"leftAt": round(time.time()), "rank": guild_data_s["members"][member]["rank"]}
            leftlist.append(member)
            
    for leftpeople in leftlist:
        guild_data_s["members"].pop(leftpeople)

    for world in OnlineServers:
        for member in gd["members"]:
            try:
                list(OnlineServers[world]).index(member["name"])
                guild_data_e["members"][member["name"]]["lastSeen"] = round(time.time())
            except:
                pass

    with open(path, 'w') as f:
        json.dump(guild_data_e, f)
