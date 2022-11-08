import requests
import os
import datetime
import time
import json

script_path = os.path.dirname(os.path.realpath(__file__))

if not os.path.isdir(os.path.join(script_path, 'datafiles')):
    os.mkdir(os.path.join(script_path, 'datafiles'))

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

def updateplayer_fdata(name):
    # try:
    #     playerdata[name]
    #     if round(time.time())-playerdata[name]["lastUpdate"]<3600: 
    #         return
    # except:
    #     pass
    
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
        "stats": {
            "playtime": data["meta"]["playtime"],
            "mobsKilled": 0,
            "blocksWalked": 0,
            "logins": 0,
            "deaths": 0
        }
    }
    if data["guild"]["name"]:
        player_fdata["guild"] = {"name": data["guild"]["name"],"rank": data["guild"]["rank"]}
        guildsdata[data["guild"]["name"]] = {"name": data["guild"]["name"]}
    for character in data["characters"]:
        for dungeon in data["characters"][character]["dungeons"]["list"]:
            try:
                player_fdata["stats"][dungeon["name"]] += dungeon["completed"]
            except:
                player_fdata["stats"][dungeon["name"]] = dungeon["completed"]
        for raid in data["characters"][character]["raids"]["list"]:
            try:
                player_fdata["stats"][raid["name"]] += raid["completed"]
            except:
                player_fdata["stats"][raid["name"]] = raid["completed"]
        player_fdata["stats"]["mobsKilled"] += data["characters"][character]["mobsKilled"]
        # player_fdata["stats"]["mobsKilled"] += data["characters"][character]["blocksWalked"]
        # player_fdata["stats"]["mobsKilled"] += data["characters"][character]["logins"]
        # player_fdata["stats"]["mobsKilled"] += data["characters"][character]["deaths"]
    playerdata[name] = player_fdata
    time.sleep(0.05)

# updateplayer_fdata("Lotting")
# updateplayer_fdata("nip_nop")
for server in OnlineServers:
    for player in OnlineServers[server]:
        updateplayer_fdata(player)
    with open(playerdatapath, 'w') as f:
        json.dump(playerdata, f)
    with open(guildsdatapath, 'w') as f:
        json.dump(guildsdata, f)

