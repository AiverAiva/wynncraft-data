import os
import requests
import time
from pymongo import MongoClient
from guild import process_all_guilds

# MongoDB connection
mongodb_uri = os.getenv('MONGODB_URI')  # Get the MongoDB URI from environment variable
client = MongoClient(mongodb_uri)  # Connect to MongoDB using the URI
db = client['wynnpool']
player_data_collection = db['player_data']

# API URLs
PLAYER_LIST_URL = 'https://api.wynncraft.com/v3/player?identifier=uuid'
PLAYER_DATA_URL_TEMPLATE = 'https://api.wynncraft.com/v3/player/{uuid}?fullResult'

# Collect all guild UUIDs in this set to avoid duplicates
collected_guild_uuids = {}

def fetch_player_uuids():
    """Fetch the list of player UUIDs from Wynncraft API."""
    try:
        response = requests.get(PLAYER_LIST_URL)
        if response.status_code == 200:
            player_data = response.json()
            player_uuids = list(player_data.get('players', {}).keys())
            print(f"Fetched {len(player_uuids)} player UUIDs.")
            return player_uuids
        else:
            raise Exception(f"Failed to fetch player UUIDs. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching player UUIDs: {e}")
        return []


def fetch_player_data(uuid):
    """Fetch the detailed player data from Wynncraft API for a specific UUID."""
    try:
        url = PLAYER_DATA_URL_TEMPLATE.format(uuid=uuid)
        response = requests.get(url)
        if response.status_code == 200:
            player_data = response.json()
            print(f"Successfully fetched data for UUID: {uuid}")
            return player_data
        elif response.status_code == 404:
            print(f"Player with UUID {uuid} not found.")
            return None
        else:
            raise Exception(f"Failed to fetch player data for UUID {uuid}. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching data for UUID {uuid}: {e}")
        return None


def store_or_update_player_data(player_data):
    """Store or update the player data in the player_data collection."""
    uuid = player_data.get('uuid')
    if not uuid:
        print("UUID not found in player data, skipping.")
        return

    existing_data = player_data_collection.find_one({"uuid": uuid})

    if existing_data:
        # Update the existing document
        update_result = player_data_collection.update_one(
            {"_id": existing_data["_id"]}, 
            {"$set": player_data}
        )
        if update_result.modified_count > 0:
            print(f"Player data for UUID {uuid} updated successfully.")
        else:
            print(f"No changes were made to the player data for UUID {uuid}.")
    else:
        # Insert a new document if it doesn't exist
        player_data_collection.insert_one(player_data)
        print(f"New player data for UUID {uuid} inserted successfully.")


def collect_guild_uuid(player_data):
    """Collect the unique guild UUID if it exists in the player data."""
    guild_info = player_data.get('guild')
    if guild_info and 'uuid' in guild_info and 'name' in guild_info and 'prefix' in guild_info:
        guild_name = guild_info['name']
        guild_uuid = guild_info['uuid']
        guild_prefix = guild_info['prefix']

        collected_guild_uuids[guild_name] = {
            'uuid': guild_uuid,
            'prefix': guild_prefix
        }

        print(f"Collected guild '{guild_name}' with UUID: {guild_uuid} and prefix: {guild_prefix}")


def process_all_players():
    """Fetch the player UUIDs, then request player data for each UUID and store it."""
    try:
        # Step 1: Fetch all player UUIDs from the Wynncraft API
        player_uuids = fetch_player_uuids()

        if not player_uuids:
            print("No player UUIDs found.")
            return

        print(f"Processing {len(player_uuids)} player UUIDs...")

        for uuid in player_uuids:
            try:
                # Step 2: Fetch the player data for this UUID
                player_data = fetch_player_data(uuid)
                if not player_data:
                    continue

                # Step 3: Store or update player data in MongoDB
                store_or_update_player_data(player_data)

                # Step 4: Collect unique guild UUID from the player data
                collect_guild_uuid(player_data)

                time.sleep(0.2)
            except Exception as e:
                print(f"An error occurred while processing UUID '{uuid}': {e}")

        print(f"Finished processing all players. Collected {len(collected_guild_uuids)} unique guild UUIDs.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    process_all_players()
    process_all_guilds(collected_guild_uuids)