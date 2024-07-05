# Local Imports
from src.logger_setup import setup_logger
from src.database import Database
from src.ping import send_ping

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



def process_ping(before, after):
    try:
        # Check conditions for sending a ping
        after_price = after.get('price')
        if after_price is None:
            return
        after_rrp = after.get('rrp')
        after_stock_available = after.get('stock-available')
        before_price = before.get('price', after_price + 1)  # Use after_price + 1 if no before_price
        before_stock_available = before.get('stock-available', False)

        if after_price < after_rrp:
            if after_price < before_price and after_stock_available:
                send_ping(db, after)
            if after_stock_available and not before_stock_available:
                send_ping(db, after)

    except Exception as error:
        logger.error(error)



def extract_changes(before, after):
    """Get the difference between before and after documents."""
    diff = {}
    for key in after:
        if key not in before or before[key] != after[key]:
            diff[key] = {'before': before.get(key), 'after': after[key]}
    return diff



# Listen for database changes
async def listen_for_database_changes(collection):
    pipeline = [{'$match': {'operationType': "update"}}]

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

                process_ping(before, after)

    except Exception as error:
        logger.error(error)



# Handle Bot Boot.
@bot.event
async def on_ready():
    print(f"{bot.user} is now online.")
    logger.info("Bot is running")

    collection_to_watch = db.config_products_col.distinct('data-table')
    threads = []

    for collection_name in collection_to_watch:
        thread = threading.Thread(target=lambda: asyncio.run(listen_for_database_changes(db[collection_name])), daemon=True)
        threads.append(thread.start())



bot.run(bot_token)