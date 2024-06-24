import os 
import discord
import asyncio
import threading
import json
from dotenv import load_dotenv
from pymongo import MongoClient


# Loading Data Securely
load_dotenv()
botToken = os.getenv('botToken')
mongoURL = os.getenv('mongoURL')

# Bot Setup
intents = discord.Intents.default()
bot = discord.Client(intents=intents)

# MongoDB Setup
client = MongoClient(f"{mongoURL}")
db = client['flippifyDB']
productRolesTable = db['products.roles']
legoScraperTable = db['scraper.lego-retirement-deals']
electronicsScraperTable = db['scraper.electronics']

# Load configuration file
with open('config.json') as config_file:
    config = json.load(config_file)



# Fetching the discord channel id associated with each type of deal to know where to post deals.
def getChannelID(dealType):
    scraper = productRolesTable.find_one({'deal_type': dealType})
    if scraper:
        print(f"Fetched Channel ID for {dealType}: {scraper['channel_id']}")
        return scraper['channel_id']
    return None



# Formatting field names for embeds.
def formatFieldName(fieldName):
    return fieldName.replace('_', ' ').capitalize()



# Posting deals in discord
async def postDeal(deal, channelID, fields):
    print("Preparing to post deal.")
    channel = bot.get_channel(channelID)

    if channel:
        try:
            print("Found Channel...")
            embed = discord.Embed(title=deal.get('product_name', 'Deal Found!'), url=deal.get('link', ''))
            for field in fields:
                if field in deal:
                    embed.add_field(name=formatFieldName(field), value=deal[field], inline=False)
            print("Sending Embed..")
            await channel.send(embed=embed)
            print("Embed sent successfully.")
        except discord.DiscordException as e:
            print(f"Failed to send embed: {e}")
    else:
        print(f"Channel with ID {channelID} not found.")



# Listen for database changes
async def listenToDbChanges():
    pipeline = [{'$match': {'operationType': 'insert'}}]

    try:
        # Fetching all tables to watch from productRolesTable
        tablesToWatch = productRolesTable.distinct('data_table')

        streams = []
        with client.start_session() as session:
            for tableName in tablesToWatch:
                table = db[tableName]
                streams.append(table.watch(pipeline, session=session))
                
            while True:
                change = None
                while not change:
                    for stream in streams:
                        change = stream.try_next()
                        if change:
                            break
                    await asyncio.sleep(1)
                
                # Process the change
                print("New deal detected.")
                deal = change['fullDocument']
                deal_type = deal['type']
                channel_id = getChannelID(deal_type)
                fields = config.get(deal_type, {}).get('fields', [])
                if channel_id:
                    asyncio.run_coroutine_threadsafe(postDeal(deal, channel_id, fields), bot.loop)
                    
    except Exception as e:
        print(f"Error listening to database changes: {e}")


# Handle Bot Boot.
@bot.event
async def on_ready():
    print(f"{bot.user} is now online.")
    threading.Thread(target=lambda: asyncio.run(listenToDbChanges()), daemon=True).start()



bot.run(botToken)