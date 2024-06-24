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
        print(f"Fetched Channel ID for {dealType}: {scraper['channel_id']}")
        return scraper['channel_id']
    return None



# Posting deals in discord
async def postDeal(deal, channelID):
    print("Preparing to post deal.")
    channel = bot.get_channel(channelID)
    if channel:
        try:
            print("Found Channel")
            embed = discord.Embed(title=deal['product_name'], url=deal['link'])
            embed.add_field(name="Price", value=deal['price'])
            print("Sending Embed.")
            await channel.send(embed=embed)
            print("Embed sent successfully.")
        except discord.DiscordException as e:
            print(f"Failed to send embed: {e}")
    else:
        print(f"Channel with ID {channelID} not found.")


# Listen for database changes
def listenToDbChanges():
    pipeline = [{'$match': {'operationType': 'insert'}}]
    with webScrapersTable.watch(pipeline) as stream:
        for change in stream:
            print("New Deal Detected.")
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