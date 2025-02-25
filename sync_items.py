import os
import requests
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

# MongoDB connection setup
DB_NAME = 'wynnpool'
COLLECTION_ITEM = 'item_data'

mongodb_uri = os.getenv('MONGODB_URI')  
client = MongoClient(mongodb_uri)
db = client[DB_NAME]
items_collection = db[COLLECTION_ITEM]

API_URL = "https://api.wynncraft.com/v3/item/database?fullResult"

def fetch_api_data():
    try:
        response = requests.get(API_URL)
        response.raise_for_status()  # Will raise an error for non-2xx status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from API: {e}")
        return {}

def sync_items():
    # Fetch the latest data from the API
    api_data = fetch_api_data()

    if not api_data:
        print("No data retrieved from API.")
        return

    print("Cleaning up the existing item data collection...")
    items_collection.delete_many({})  # Clears the collection

    item_docs = []

    for item_id, details in api_data.items():
        item_data = { "id": item_id, **details }
        item_docs.append(item_data)

    try:
        print("Inserting items into database...")
        items_collection.insert_many(item_docs)
        print("Item sync successful!")
    except BulkWriteError as e:
        print(f"Error inserting data: {e}")

if __name__ == "__main__":
    sync_items()
