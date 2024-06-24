import os 
import discord
from dotenv import load_dotenv
from pymongo import MongoClient
from discord.utils import get

# Loading Data Securely
load_dotenv()
botToken = os.getenv('botToken')
mongoURL = os.getenv('mongoURL')

# Bot Setup
intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)

# MongoDB Setup
client = MongoClient(f"{mongoURL}")
db = client['flippifyDB']
userTable = db['users']
productRolesTable = db['products.roles']