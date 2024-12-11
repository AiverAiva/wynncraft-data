import json
import requests
import time
from pymongo import MongoClient
import os

# Database configuration
DB_NAME = 'wynnpool'
COLLECTION_EVENTS = 'guild_member_events'
COLLECTION_GUILD_DATA = 'guild_data'

# MongoDB connection
mongodb_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongodb_uri)
db = client[DB_NAME]
guild_data_collection = db[COLLECTION_GUILD_DATA]
events_collection = db[COLLECTION_EVENTS]

# API URL to get the list of guilds
GUILD_LIST_URL = 'https://api.wynncraft.com/v3/guild/list/guild'


def fetch_guild_list():
    """Fetch the list of all guilds from the API."""
    try:
        response = requests.get(GUILD_LIST_URL)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch guild list. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching guild list: {e}")
        return {}


def fetch_guild_data(guild_name):
    """Fetch the latest guild data from the API for a specific guild."""
    try:
        api_url = f'https://api.wynncraft.com/v3/guild/{guild_name}?identifier=uuid'
        response = requests.get(api_url)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Failed to fetch data for guild '{guild_name}'. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching data for guild '{guild_name}': {e}")
        return None


def get_existing_guild_data(guild_uuid):
    """Get the most recent stored guild data from MongoDB using guild UUID."""
    return guild_data_collection.find_one({"uuid": guild_uuid}, sort=[("_id", -1)])


def store_guild_data(guild_data):
    """Store or update the fetched guild data into MongoDB."""
    guild_data['timestamp'] = int(time.time())  # Add timestamp

    # Extract the guild UUID for the current guild
    guild_uuid = guild_data.get('uuid')
    if not guild_uuid:
        raise Exception("Guild UUID not found in the API response.")

    # Check if this guild data already exists (using guild UUID as the unique key)
    existing_data = guild_data_collection.find_one({"uuid": guild_uuid})

    if existing_data:
        # Update the existing document
        update_result = guild_data_collection.update_one(
            {"_id": existing_data["_id"]}, 
            {"$set": guild_data}
        )
        if update_result.modified_count > 0:
            print(f"Guild data for UUID {guild_uuid} updated successfully.")
        else:
            print(f"No changes were made to the guild data for UUID {guild_uuid}.")
    else:
        # Insert a new document if it doesn't exist
        guild_data_collection.insert_one(guild_data)
        print(f"New guild data for UUID {guild_uuid} inserted successfully.")


def detect_member_changes(old_data, new_data):
    """Detect member join, leave, and rank changes."""
    if not old_data:
        return

    old_members = extract_members(old_data)
    new_members = extract_members(new_data)
    guild_uuid = new_data.get('uuid', 'Unknown UUID')
    guild_name = new_data.get('name', 'Unknown Name')

    # 1. Check for new members (join)
    for uuid, member in new_members.items():
        if uuid not in old_members:
            event = {
                'timestamp': int(time.time()),
                'event': 'join',
                'uuid': new_member['uuid'],
                'name': member['username'],
                'guild_uuid': guild_uuid,
                'guild_name': guild_name
            }
            events_collection.insert_one(event)
            print(f"New member joined: {member['username']}")

    # 2. Check for members who left
    for uuid, member in old_members.items():
        if uuid not in new_members:
            event = {
                'timestamp': int(time.time()),
                'event': 'leave',
                'uuid': new_member['uuid'],
                'name': member['username'],
                'guild_uuid': guild_uuid,
                'guild_name': guild_name,
                'rank': member['rank']
            }
            events_collection.insert_one(event)
            print(f"Member left: {member['username']}")

    # 3. Check for rank changes
    for uuid, new_member in new_members.items():
        if uuid in old_members:
            old_member = old_members[uuid]
            if old_member['rank'] != new_member['rank']:
                event = {
                    'timestamp': int(time.time()),
                    'event': 'rank_change',
                    'uuid': new_member['uuid'],
                    'name': new_member['username'],
                    'guild_uuid': guild_uuid,
                    'guild_name': guild_name,
                    'old_rank': old_member['rank'],
                    'new_rank': new_member['rank']
                }
                events_collection.insert_one(event)
                print(f"Rank change for {new_member['username']}: {old_member['rank']} -> {new_member['rank']}")


def extract_members(guild_data):
    """Extract members as a flat list of users with their ranks."""
    members = {}
    for rank, rank_members in guild_data.get('members', {}).items():
        if rank != 'total':  # Skip 'total' field
            for uuid, member_data in rank_members.items():
                members[uuid] = {
                    'username': member_data['username'],
                    'rank': rank,
                    'joined': member_data['joined']
                }
    return members


def process_all_guilds(guild_list):
    """Process all guilds from the guild list."""
    try:
        # Step 1: Fetch the list of all guilds
        if not guild_list:
            print("No guilds found in the guild list.")
            return

        total_guilds = len(guild_list)
        print(f"Total guilds to process: {total_guilds}")
        for guild_name, guild_info in guild_list.items():
            try:
                print(f"\nProcessing guild: {guild_name} (UUID: {guild_info['uuid']})")

                # Step 2: Fetch the latest data for this guild
                new_data = fetch_guild_data(guild_name)
                if not new_data:
                    continue

                # Step 3: Get the existing data from MongoDB
                old_data = get_existing_guild_data(guild_info['uuid'])

                # Step 4: Detect changes (join, leave, rank change)
                detect_member_changes(old_data, new_data)

                # Step 5: Store or update the new guild data in MongoDB
                store_guild_data(new_data)
            except Exception as e:
                print(f"An error occurred while processing guild '{guild_name}': {e}")

        print("Finished processing all guilds.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    process_all_guilds(fetch_guild_list())
