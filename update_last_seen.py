import os
import time
import asyncio
import aiohttp
from pymongo import MongoClient, UpdateOne
from concurrent.futures import ThreadPoolExecutor

# Database configuration
DB_NAME = 'wynnpool'
COLLECTION_GUILD_DATA = 'guild_data'
COLLECTION_GUILD_LAST_SEEN = 'guild_last_seen'
COLLECTION_GUILD_ONLINE_COUNT = 'guild_online_count'

# API URL for Wynncraft player list
PLAYER_API_URL = 'https://api.wynncraft.com/v3/player?identifier=uuid'

# MongoDB connection
mongodb_uri = os.getenv('MONGODB_URI')
client = MongoClient(mongodb_uri)
db = client[DB_NAME]
guild_last_seen_collection = db[COLLECTION_GUILD_LAST_SEEN]
guild_online_count_collection = db[COLLECTION_GUILD_ONLINE_COUNT]

async def fetch_player_list(session):
    """Fetch the player list from Wynncraft API asynchronously."""
    try:
        async with session.get(PLAYER_API_URL, timeout=10) as response:
            if response.status == 200:
                player_data = await response.json()
                player_uuids = set(player_data['players'].keys())
                print(f"Fetched {len(player_uuids)} player UUIDs from Wynncraft API.")
                return player_uuids
            else:
                raise Exception(f"Failed to fetch player list. Status code: {response.status}")
    except Exception as e:
        print(f"Error fetching player list: {e}")
        return set()

async def process_guild(guild, player_uuids, current_time):
    """Process each guild to prepare updates."""
    guild_name = guild.get('name', 'Unknown')
    guild_uuid = guild.get('uuid', 'Unknown')
    members = extract_members(guild)

    guild_last_seen_data = {
        'guild_name': guild_name,
        'guild_uuid': guild_uuid,
        'members': {}
    }

    online_count = 0

    for uuid, member in members.items():
        if uuid in player_uuids:
            guild_last_seen_data['members'][uuid] = {'lastSeen': current_time}
            online_count += 1
            print(f"Updated lastSeen for member {member['username']} (UUID: {uuid}) in guild {guild_name}.")

    last_seen_update = (guild_uuid, guild_last_seen_data) if guild_last_seen_data['members'] else None
    online_count_update = {
        'guild_name': guild_name,
        'guild_uuid': guild_uuid,
        'timestamp': current_time,
        'count': online_count
    } 

    return last_seen_update, online_count_update

async def update_last_seen_and_online_count(guilds):
    async with aiohttp.ClientSession() as session:
        player_uuids = await fetch_player_list(session)
        if not player_uuids:
            print("No player UUIDs fetched. Exiting.")
            return

        current_time = int(time.time())
        last_seen_updates = []
        online_count_updates = []

        # Prepare updates concurrently
        tasks = []
        for guild in guilds:
            tasks.append(process_guild(guild, player_uuids, current_time))

        results = await asyncio.gather(*tasks)

        for last_seen_update, online_count_update in results:
            if last_seen_update:
                last_seen_updates.append(last_seen_update)
            if online_count_update:
                online_count_updates.append(online_count_update)

        # Perform bulk updates
        if last_seen_updates:
            await run_in_executor(batch_update_last_seen, last_seen_updates)
        if online_count_updates:
            await run_in_executor(batch_insert_online_count, online_count_updates)

async def run_in_executor(func, *args):
    """Run a synchronous function in a thread pool executor."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        return await loop.run_in_executor(executor, func, *args)

def batch_update_last_seen(updates):
    """Batch update last seen data."""
    operations = [UpdateOne({'guild_uuid': guild_uuid}, {'$set': data}, upsert=True) for guild_uuid, data in updates]
    if operations:
        try:
            result = guild_last_seen_collection.bulk_write(operations)
            print(f"Bulk updated last seen data for {result.modified_count} guilds.")
        except Exception as e:
            print(f"Error during bulk update of last seen data: {e}")

def batch_insert_online_count(online_counts):
    """Batch insert online count data."""
    if online_counts:
        try:
            guild_online_count_collection.insert_many(online_counts)
            print("Inserted online count data for multiple guilds.")
        except Exception as e:
            print(f"Error inserting online count data: {e}")

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

def delete_old_datasets():
    """Delete datasets older than 3 days."""
    three_days_ago = int(time.time()) - 3 * 24 * 60 * 60  # Calculate the timestamp for 3 days ago
    try:
        # Remove old records from the guild_online_count collection
        deleted_online_count = guild_online_count_collection.delete_many({
            "timestamp": {"$lt": three_days_ago}
        })
        print(f"Deleted {deleted_online_count.deleted_count} outdated records from guild_online_count.")
    except Exception as e:
        print(f"An error occurred while deleting outdated datasets: {e}")

def main():
    try:
        start_time = time.time()
        guilds = list(db[COLLECTION_GUILD_DATA].find())  # Fetch all guilds once
        asyncio.run(update_last_seen_and_online_count(guilds))
        delete_old_datasets()  # Call the function to remove outdated datasetsjjjj
        print("Finished updating lastSeen and online counts for all guilds. Operation took:", time.time() - start_time, "sec")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
