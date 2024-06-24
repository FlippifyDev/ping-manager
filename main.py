import os 
import discord
import asyncio
import threading
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
userTable = db['users']
productRolesTable = db['products.roles']
webScrapersTable = db['webscrapers']



# Fetching the discord channel id associated with each type of deal to know where to post deals.
def getChannelID(dealType):
    scraper = productRolesTable.find_one({'deal_type': dealType})
    if scraper:
        return scraper['channel_id']
    return None



# Posting deals in discord
async def postDeal(deal, channelID):
    channel = bot.get_channel(channelID)
    if channel:
        embed = discord.Embed(title=deal['product_name'], url=deal['link'])
        embed.add_field(name="Price", value=deal['price'])
        await channel.send(embed=embed)



# Listen for database changes
def listenToDbChanges():
    pipeline = [{'$match': {'operationType': 'insert'}}]
    with webScrapersTable.watch(pipeline) as stream:
        for change in stream:
            deal = change['fullDocument']
            dealType = deal['type']
            channelID = getChannelID(dealType)
            if channelID:
                asyncio.run_coroutine_threadsafe(postDeal(deal, channelID), bot.loop)



# Handle Bot Boot.
@bot.event
async def on_ready():
    print(f"{bot.user} is now online.")
    threading.Thread(target=listenToDbChanges, daemon=True).start()



bot.run(botToken)