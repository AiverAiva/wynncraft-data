from pymongo import MongoClient
import requests
import os
import time
mongodb_uri = os.getenv("MONGODB_URI")
client = MongoClient(mongodb_uri)
db = client["wynnpool"]
collection = db["users"]

# Find only users that already have minecraftProfile.uuid
users_with_uuid = collection.find(
    {"minecraftProfile.uuid": {"$exists": True, "$ne": None}},
    {"minecraftProfile.uuid": 1}
)

for user in users_with_uuid:
    uuid = user["minecraftProfile"]["uuid"]

    try:
        response = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}")

        # Mojang success
        if response.status_code == 200:
            data = response.json()
            username = data.get("name")

            if username:
                result = collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"minecraftProfile.name": username}}
                )
                print(f"Updated user {user['_id']} UUID {uuid} -> name {username}")

        # Mojang rate limit
        elif response.status_code == 429:
            print("Rate limited by Mojang API. Sleeping for 60 seconds...")
            time.sleep(60)
            continue

        else:
            print(f"UUID {uuid} lookup error: {response.status_code}")

    except Exception as e:
        print(f"Error processing user {user['_id']} (UUID {uuid}): {e}")