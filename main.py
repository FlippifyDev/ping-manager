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
productRolesTable = db['products.roles']
legoScraperTable = db['scraper.lego-retirement-deals']
electronicsScraperTable = db['scraper.electronics']



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
async def listenToDbChanges():
    pipeline = [{'$match': {'operationType': 'insert'}}]

    try:
        # Watching both collections in a single loop
        with client.start_session() as session:
            with legoScraperTable.watch(pipeline, session=session) as lego_stream, \
                 electronicsScraperTable.watch(pipeline, session=session) as electronics_stream:
                
                while True:
                    # Wait for either stream to have a new document
                    change = None
                    while not change:
                        change = lego_stream.try_next() or electronics_stream.try_next()
                        await asyncio.sleep(1)
                    
                    # Process the change
                    print("New deal detected.")
                    deal = change['fullDocument']
                    deal_type = deal['type']
                    channel_id = getChannelID(deal_type)
                    if channel_id:
                        asyncio.run_coroutine_threadsafe(postDeal(deal, channel_id), bot.loop)

    except Exception as e:
        print(f"Error listening to database changes: {e}")


# Handle Bot Boot.
@bot.event
async def on_ready():
    print(f"{bot.user} is now online.")
    threading.Thread(target=lambda: asyncio.run(listenToDbChanges()), daemon=True).start()



bot.run(botToken)