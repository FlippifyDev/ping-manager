# Local Imports
from src.scraper_handers import handle_should_send_ping
from src.logger_setup import setup_logger, delete_previous_logs_on_start
from src.database import Database
from src.ping import send_ping, send_test_ping

# External Imports
from dotenv import load_dotenv

import threading
import asyncio
import discord
import json
import os


logger = setup_logger("PING-MANAGER", "ping-manager")

# Loading Data Securely
load_dotenv()
bot_token = os.getenv('BOT_TOKEN')

# Bot Setup
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# MongoDB Setup
db = Database()


# Load configuration file
with open('config.json') as file:
    config = json.load(file)



def extract_changes(before, after):
    """Get the difference between before and after documents."""
    diff = {}
    for key in after:
        if key not in before or before[key] != after[key]:
            diff[key] = {'before': before.get(key), 'after': after[key]}
    return diff



# Listen for database changes
async def listen_for_database_changes(collection):
    col_name = collection.name
    if "scraper" in col_name:
        pipeline = [{'$match': {'operationType': {"$in": ["update"]}}}]
    else:
        pipeline = [{"$match": {"operationType": {"$in": ["insert", "update"]}}}]

    try:
        with collection.watch(pipeline, full_document='updateLookup', full_document_before_change='whenAvailable') as stream:
            for change in stream:
                # Process the change
                operation_type = change['operationType']
                if operation_type == 'insert':
                    after = change['fullDocument']
                    before = None
                elif operation_type == 'update':
                    after = change['fullDocument']
                    before = change.get('fullDocumentBeforeChange', {})
                elif operation_type == 'replace':
                    after = change['fullDocument']
                    before = change.get('fullDocumentBeforeChange', {})

                if "scraper" in col_name:
                    if handle_should_send_ping(db, before, after) is True:
                        send_ping(db, after)
                elif col_name == "subscription.servers":
                    send_test_ping(change.get("updateDescription", {}).get("updatedFields", ""))

    except Exception as error:
        logger.error(error)



# Handle Bot Boot.
@bot.event
async def on_ready():
    logger.info(f"{bot.user} is now online.")
    logger.info("Bot is running")

    collections_to_watch = [db["subscription.servers"]]
    collections_to_watch += [db[col] for col in db.config_products_col.distinct('data-table') if db[col] is not None]
    threads = []

    for collection in collections_to_watch:
        thread = threading.Thread(target=lambda: asyncio.run(listen_for_database_changes(collection)), daemon=True)
        threads.append(thread.start())


delete_previous_logs_on_start("ping-manager")
bot.run(bot_token)