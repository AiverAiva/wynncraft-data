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
    
def get_item_changelog(item_id):
    """Fetch changelog for a specific item, sorted by timestamp in descending order."""
    return list(changelog_collection.find({"itemName": item_id}).sort("timestamp", -1))

def sync_items():
    # Fetch the latest data from the API
    api_data = fetch_api_data()

    if not api_data:
        print("No data retrieved from API.")
        return

    print("Cleaning up the existing item data collection...")
    items_collection.delete_many({})  # Clears the collection

    item_docs = []
    items_with_changelog = 0

    for item_id, details in api_data.items():
        changelog = get_item_changelog(item_id)
        item_data = { "id": item_id, **details }
        if changelog:
            item_data["changelog"] = changelog
            items_with_changelog += 1
        item_docs.append(item_data)
        

    try:
        print("Inserting items into database...")
        items_collection.insert_many(item_docs)
        print(f"Item sync successful! {items_with_changelog} items have changelogs.")
    except BulkWriteError as e:
        print(f"Error inserting data: {e}")

if __name__ == "__main__":
    sync_items()
