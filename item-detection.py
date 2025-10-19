import time
from pymongo import MongoClient
import requests
import json
import os

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
    response = requests.get(API_URL)
    if response.status_code == 200:
        return response.json()
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

    # Check for added items
    for item_id, item in current_data.items():
        if item_id not in previous_data:
            item_change = {
                "itemName": item_id,
                "status": "add",
                "timestamp": timestamp,
                **item  # Spread other item stats directly
            }
            changes.append(item_change)

    # Check for removed items
    for item_id, item in previous_data.items():
        if item_id not in current_data:
            item_change = {
                "itemName": item_id,
                "status": "remove",
                "timestamp": timestamp,
                **item  # Include previous item stats
            }
            changes.append(item_change)

    # Check for modified items
    for item_id, item in current_data.items():
        if item_id in previous_data and item != previous_data[item_id]:
            prev_item = previous_data[item_id]
            curr_item = item

            # Ensure both items are dictionaries before attempting key removal
            if isinstance(prev_item, dict) and isinstance(curr_item, dict):
                # Deep copy to avoid modifying the original data
                temp_prev = prev_item.copy()
                temp_curr = curr_item.copy()

                # Safely remove customModelData if present
                try:
                    if "icon" in temp_prev and "icon" in temp_curr:
                        if "value" in temp_prev["icon"] and "value" in temp_curr["icon"]:
                            if isinstance(temp_prev["icon"]["value"], dict) and isinstance(temp_curr["icon"]["value"], dict):
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
                "after": curr_item
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
        print('New item datasets saved!')
        
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()