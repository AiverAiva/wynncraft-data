import time
from pymongo import MongoClient
import requests
import json
import os
# from dotenv import load_dotenv
# load_dotenv()

# The URL of the Wynncraft API
API_URL = "https://api.wynncraft.com/v3/item/database?fullResult"

# MongoDB Configuration
DB_NAME = "wynnpool"
COLLECTION_ITEM_CHANGELOG = "item_changelog"

# MongoDB Connection
mongodb_uri = os.getenv("MONGODB_URI")
client = MongoClient(mongodb_uri)
db = client[DB_NAME]
item_changelog_collection = db[COLLECTION_ITEM_CHANGELOG]

# Path to store the previous data
DATA_FILE = "previous_item_data.json"


# Function to fetch the data from the API
def fetch_data():
    api_key = os.getenv("WYNNCRAFT_API_KEY")
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    response = requests.get(API_URL, headers=headers)
    if response.status_code == 200:
        data = response.json()
        # API returns a list; index by internalName for consistent lookup
        if isinstance(data, list):
            return {
                item["internalName"]: item for item in data if "internalName" in item
            }
        return data
    else:
        raise Exception(f"Failed to fetch data. Status code: {response.status_code}")


# Function to load previous data from the file, if it exists
def load_previous_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as file:
            return json.load(file)
    else:
        return {}


# Function to save current data to a file for future comparisons
def save_current_data(data):
    with open(DATA_FILE, "w") as file:
        json.dump(data, file, indent=4)


# Function to compare previous and current data
def compare_items(previous_data, current_data, timestamp):
    changes = []

    # Build lookup dicts using internalName as the unique identifier
    previous_by_internal = {
        item.get("internalName"): item
        for item in previous_data.values()
        if "internalName" in item
    }
    current_by_internal = {
        item.get("internalName"): item
        for item in current_data.values()
        if "internalName" in item
    }

    previous_ids = set(previous_by_internal.keys())
    current_ids = set(current_by_internal.keys())

    # Check for added items
    for item_id in current_ids - previous_ids:
        item = current_by_internal[item_id]
        item_change = {
            "itemName": item_id,
            "status": "add",
            "timestamp": timestamp,
            **item,  # Spread other item stats directly
        }
        changes.append(item_change)

    # Check for removed items
    for item_id in previous_ids - current_ids:
        item = previous_by_internal[item_id]
        item_change = {
            "itemName": item_id,
            "status": "remove",
            "timestamp": timestamp,
            **item,  # Include previous item stats
        }
        changes.append(item_change)

    # Check for modified items
    for item_id in previous_ids & current_ids:
        prev_item = previous_by_internal[item_id]
        curr_item = current_by_internal[item_id]

        if prev_item == curr_item:
            continue

        # Ensure both items are dictionaries before attempting key removal
        if isinstance(prev_item, dict) and isinstance(curr_item, dict):
            # Deep copy to avoid modifying the original data
            temp_prev = prev_item.copy()
            temp_curr = curr_item.copy()

            # Safely remove customModelData if present
            try:
                if "icon" in temp_prev and "icon" in temp_curr:
                    if "value" in temp_prev["icon"] and "value" in temp_curr["icon"]:
                        if isinstance(temp_prev["icon"]["value"], dict) and isinstance(
                            temp_curr["icon"]["value"], dict
                        ):
                            temp_prev["icon"]["value"].pop("customModelData", None)
                            temp_curr["icon"]["value"].pop("customModelData", None)
            except (KeyError, TypeError):
                pass  # Ignore errors if the structure is incorrect

            # If the items are now identical after ignoring customModelData, skip it
            if temp_prev == temp_curr:
                continue

        # Otherwise, register the modification
        item_change = {
            "itemName": item_id,
            "status": "modify",
            "timestamp": timestamp,
            "before": prev_item,
            "after": curr_item,
        }
        changes.append(item_change)

    return changes


def main():
    try:
        # Fetch the current data
        current_data = fetch_data()

        # Load the previous data
        previous_data = load_previous_data()

        # Generate a consistent timestamp for all changes in this update
        timestamp = int(time.time())

        # Compare the previous and current data
        changes = compare_items(previous_data, current_data, timestamp)

        if changes:
            # Insert changes into MongoDB
            item_changelog_collection.insert_many(changes)
            print(f"Stored {len(changes)} item changes into the database.")
            print("CHANGES_FOUND")

        # Save the current data for future comparisons
        save_current_data(current_data)
        print("New item datasets saved!")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
