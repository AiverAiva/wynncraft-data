import requests
from pymongo import DeleteOne, MongoClient, UpdateOne
import os
import time

# Wynncraft aspect endpoints
endpoints = [
    "https://api.wynncraft.com/v3/aspects/mage",
    "https://api.wynncraft.com/v3/aspects/archer",
    "https://api.wynncraft.com/v3/aspects/shaman",
    "https://api.wynncraft.com/v3/aspects/warrior",
    "https://api.wynncraft.com/v3/aspects/assassin",
]
DB_NAME = "wynnpool"
COLLECTION_ITEM = "aspect_data"

# MongoDB setup
mongodb_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongodb_uri)
db = client[DB_NAME]
aspects_col = db["aspect_data"]
changelog_col = db["aspect_changelog"]

# Ensure index on requiredClass
aspects_col.create_index({"requiredClass": 1})


# ---------- Fetch API ----------
def fetch_all_aspects(endpoints):
    merged = {}
    for url in endpoints:
        try:
            res = requests.get(url)
            res.raise_for_status()
            merged.update(res.json())
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
    return merged


# ---------- Save + Detect changes ----------
def save_bulk_aspects(aspects):
    timestamp = int(time.time())

    # Load existing documents for comparison
    existing_docs = list(aspects_col.find({}))
    existing_map = {doc["aspectId"]: doc for doc in existing_docs}

    new_ids = set(aspects.keys())
    old_ids = set(existing_map.keys())

    ops = []

    # 1. Detect removed aspects
    removed_ids = old_ids - new_ids
    for removed in removed_ids:
        prev_doc = existing_map[removed].copy()
        del prev_doc["_id"]

        # Log removal
        changelog_col.insert_one({
            "aspectId": removed,
            "status": "remove",
            "timestamp": timestamp,
            **prev_doc
        })

        # Remove from DB
        ops.append(DeleteOne({"aspectId": removed}))

    # 2. Handle add/modify + upsert
    for aspect_id, aspect_data in aspects.items():

        # Flatten
        curr_flat = {
            "aspectId": aspect_id,
            **aspect_data
        }

        if aspect_id not in existing_map:
            # NEW aspect
            changelog_col.insert_one({
                "aspectId": aspect_id,
                "status": "add",
                "timestamp": timestamp,
                **curr_flat
            })

        else:
            # EXISTING aspect → check modify
            prev = existing_map[aspect_id].copy()
            prev.pop("_id", None)

            if prev != curr_flat:
                changelog_col.insert_one({
                    "aspectId": aspect_id,
                    "status": "modify",
                    "timestamp": timestamp,
                    "before": prev,
                    "after": curr_flat
                })

        # Upsert document
        ops.append(
            UpdateOne(
                {"aspectId": aspect_id},
                {"$set": curr_flat},
                upsert=True
            )
        )

    if ops:
        result = aspects_col.bulk_write(ops)
        print(f"Upserts: {result.upserted_count}, Updates: {result.modified_count}")
    else:
        print("No updates needed.")


# ---------- Main ----------
if __name__ == "__main__":
    aspects = fetch_all_aspects(endpoints)
    save_bulk_aspects(aspects)