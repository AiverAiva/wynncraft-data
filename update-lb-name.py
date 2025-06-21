from pymongo import MongoClient
import requests
import os
import time

mongodb_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongodb_uri)
db = client["wynnpool"]
collection = db["verified_item_data"]

uuids = collection.distinct("uuid")

for uuid in uuids:
    try:
        response = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{uuid}")
        if response.status_code == 200:
            username = response.json().get("name")
            if username:
                result = collection.update_many({"uuid": uuid}, {"$set": {"owner": username}})
                print(f"Updated {result.modified_count} documents for UUID {uuid} -> {username}")
        elif response.status_code == 429:
            print("Rate limited by Mojang API, sleeping for 60 seconds...")
            time.sleep(60)
        else:
            print(f"UUID {uuid} not found or error: {response.status_code}")
    except Exception as e:
        print(f"Error processing UUID {uuid}: {e}")
    # time.sleep(1.1)  # Rate limit safety