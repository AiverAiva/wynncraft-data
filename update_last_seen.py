import requests
import time
from pymongo import MongoClient
import os

# Database configuration
DB_NAME = 'wynnpool'
COLLECTION_GUILD_DATA = 'guild_data'

# API URL for Wynncraft player list
PLAYER_API_URL = 'https://api.wynncraft.com/v3/player?identifier=uuid'

# MongoDB connection
mongodb_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongodb_uri)
db = client[DB_NAME]
guild_data_collection = db[COLLECTION_GUILD_DATA]


def fetch_player_list():
    """Fetch the player list from Wynncraft API."""
    try:
        response = requests.get(PLAYER_API_URL, timeout=10)
        if response.status_code == 200:
            player_data = response.json()
            player_uuids = set(player_data['players'].keys())
            print(f"Fetched {len(player_uuids)} player UUIDs from Wynncraft API.")
            return player_uuids
        else:
            raise Exception(f"Failed to fetch player list. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching player list: {e}")
        return set()


def update_last_seen_for_all_guilds(player_uuids):
    """Update the lastSeen field for all members in all guilds if their UUID is in the player list."""
    current_time = int(time.time())

    # Find all guild documents in the guild_data collection
    guilds = guild_data_collection.find()

    updated_count = 0

    for guild in guilds:
        guild_name = guild.get('guild', 'Unknown Guild')
        print(f"Processing guild: {guild_name}")
        
        # Extract members from the guild data
        members = extract_members(guild)

        for uuid, member in members.items():
            if uuid in player_uuids:
                # Update the member's lastSeen field
                update_result = guild_data_collection.update_one(
                    {'_id': guild['_id'], f'members.{member["rank"]}.{uuid}.username': member['username']},
                    {'$set': {f'members.{member["rank"]}.{uuid}.lastSeen': current_time}}
                )
                
                if update_result.modified_count > 0:
                    updated_count += 1
                    print(f"Updated lastSeen for {member['username']} (UUID: {uuid}) in guild {guild_name}")
    
    print(f"Total members updated: {updated_count}")


def extract_members(guild_data):
    """Extract members as a flat list of users with their ranks."""
    members = {}
    for rank, rank_members in guild_data.get('members', {}).items():
        if rank != 'total':  # Skip 'total' field
            for uuid, member_data in rank_members.items():
                members[uuid] = {
                    'username': member_data.get('username'),
                    'rank': rank
                }
    return members


def main():
    try:
        # Step 1: Fetch the player list from Wynncraft API
        player_uuids = fetch_player_list()
        if not player_uuids:
            print("No player UUIDs fetched. Exiting.")
            return
        
        # Step 2: Update the lastSeen field for all members in all guilds
        update_last_seen_for_all_guilds(player_uuids)
        print("Finished updating lastSeen for all guild members.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
