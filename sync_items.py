import os
import requests
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

# MongoDB connection setup
DB_NAME = 'wynnpool'
COLLECTION_ITEM = 'item_data'
COLLECTION_CHANGELOG = 'item_changelog'

mongodb_uri = os.getenv('MONGODB_URI')  
client = MongoClient(mongodb_uri)
db = client[DB_NAME]
items_collection = db[COLLECTION_ITEM]
changelog_collection = db[COLLECTION_CHANGELOG]

API_URL = "https://api.wynncraft.com/v3/item/database?fullResult"

def fetch_api_data():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Will raise an error for non-2xx status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return {}
    
def fetch_all_changelogs():
    """Fetch all changelogs at once and store in a dictionary for quick lookup."""
    changelog_data = {}
    for entry in changelog_collection.find({}, {"_id": 0}):  # Fetch all fields except _id
        item_name = entry["itemName"]
        if item_name not in changelog_data:
            changelog_data[item_name] = []
        changelog_data[item_name].append(entry)

    # Ensure all changelogs are sorted in descending order by timestamp
    for key in changelog_data:
        changelog_data[key].sort(key=lambda x: x["timestamp"], reverse=True)

    return changelog_data

def sync_items():
    # Fetch the latest data from the API
    api_data = fetch_api_data()
    if not api_data:
        print("No data retrieved from API.")
        return

    print("Fetching changelog data in bulk...")
    changelog_data = fetch_all_changelogs()
    print("Cleaning up the existing item data collection...")
    items_collection.delete_many({})  # Clears the collection

    item_docs = []
    items_with_changelog = 0

    for item_id, details in api_data.items():
        item_data = {"id": item_id, **details}
        
        if item_id in changelog_data:
            # item_data["changelog"] = changelog_data[item_id]
            items_with_changelog += 1

        item_docs.append(item_data)

    try:
        print("Inserting items into database...")
        items_collection.insert_many(item_docs, ordered=False)  # Optimized bulk insert
        print(f"Item sync successful! {items_with_changelog} items have changelogs.")
    except BulkWriteError as e:
        print(f"Error inserting data: {e}")

if __name__ == "__main__":
    sync_items()
