# Local Imports
from src.scraper_handers import lego_retirement_ping_data
from .exceptions import InvalidScraperType

# External Imports
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv

import pyshorteners
import logging
import time
import json
import os
import re

load_dotenv()

logger = logging.getLogger("PING-MANAGER")

type_tiny = pyshorteners.Shortener()


"""

# Formatting field names for embeds.
def format_field_name(field_name):
    return field_name.replace('_', ' ').capitalize()


# Posting deals in discord
async def postDeal(deal, channelID, fields):
    print("Preparing to post deal.")
    channel = bot.get_channel(channelID)

    if channel:
        try:
            embed = discord.Embed(
                title=deal.get('product-name', 'Deal Found!'),
                url=deal.get('link', ''),
                color=discord.Color.blue(),
                timestamp=datetime.now()
                )

            for field in fields:
                if field in deal:
                    print("Field:", field)
                    if field == 'image':
                        embed.set_thumbnail(url=deal['image'])
                        continue
                    if field == 'timestamp' or field == 'type':
                        continue
                    else:
                        embed.add_field(name=format_field_name(field), value=deal[field], inline=False)
            
            await channel.send(embed=embed)
            print("Embed sent successfully.")
            logger.info("")
        except discord.DiscordException as e:
            print(f"Failed to send embed: {e}")
            logger.error("Error sending embed %s" % e)
    else:
        print(f"Channel with ID {channelID} not found.")
        logger.error("Channel %s not found" % channelID) 
"""



def send_test_ping(after):
    embeds = [
        {
            "title": "Your webhook works!!",
            "description": "If this is not the channel you want the pings to go to then simply re-enter another webhook. \nThe new webhook will replace the previous one.",
            "color": 65280
        }
    ]
    webhook_url = after.get("webhook")
    if webhook_url is None:
        return
    
    webhook = DiscordWebhook(url=webhook_url, embeds=embeds, rate_limit_retry=True)
    webhook.execute()


def send_ping(db, document):
    try:
        embed = create_embed(db, document)

        # Load the webhook from the config file
        webhook_url = os.getenv(document.get("type"))
        if webhook_url == None:
            logger.critical(f"Scraper Type: {document.get('type')} has no webhook")
            return


        def send_to_webhook(webhook):
            webhook = DiscordWebhook(url=webhook, embeds=embed, rate_limit_retry=True)
            webhook.execute()

        send_to_webhook(webhook_url)
        user_webhooks = db.get_user_webhooks(document.get("type"))

        for user_webhook in user_webhooks:
            send_to_webhook(user_webhook)

        logger.info(f"Ping sent for {document.get('product-name')} on {document.get('website')}")

        time.sleep(0.5)

    except Exception as error:
        logger.critical(msg=f"Couldn't send ping for ({document.get('product-name')}) on ({document.get('link')}) | {error}")



def fetch_scraper_config(scraper_type):
    with open("config.json") as file:
        config = json.load(file)
        scraper_config = config.get(scraper_type)
        if scraper_config is None:
            raise InvalidScraperType(scraper_type)
        return scraper_config



def evaluate_expression(expression, document):
    try:
        # Create a context with document keys as variables, replacing hyphens with underscores
        context = {k.replace('-', '_'): v for k, v in document.items()}
        
        # Replace hyphens in the expression only for variable names
        expression_with_underscores = re.sub(r'\b\w+-\w+\b', lambda match: match.group().replace('-', '_'), expression)
        
        # Evaluate the expression safely within the provided document context
        return eval(expression_with_underscores, {}, context)
    except Exception as error:
        logger.error(f"Error evaluating expression '{expression}': {error}")
        return None



def format_value(value, document):
    if isinstance(value, str):
        # Handle complex expressions within curly braces
        pattern = re.compile(r"\{(.*?)\}")
        matches = pattern.findall(value)

        for match in matches:
            evaluated_result = evaluate_expression(match, document)
            if evaluated_result is not None:
                value = value.replace(f'{{{match}}}', str(evaluated_result))
            else:
                # If evaluated result is None or not found, replace the placeholder with an empty string
                value = value.replace(f'{{{match}}}', '')

        # Format the string with document values
        try:
            formatted_value = value.format(**document)
        except KeyError:
            # If a key is not found in document, replace it with an empty string
            formatted_value = re.sub(r'\{([^}]*)\}', '', value)

        # Encode to bytes, decode to ensure correct encoding handling
        formatted_value = formatted_value.encode('latin1', errors='ignore').decode('utf-8', errors='ignore')

        return formatted_value
    return value



def create_embed(db, document):
    temp_link = None
    try:
        scraper_config = fetch_scraper_config(document.get("type"))

        # Change the amazon link to a tiny url
        if (document.get("website") == "Amazon"):
            temp_link = document.get("link", "")
            document["link"] = type_tiny.tinyurl.short(temp_link)

        # Create the dictionary with the extracted and formatted data
        ping_data = {key: format_value(value, document) for key, value in scraper_config.items()}

        # Handle nested fields and format them as well
        for field in ping_data.get("fields", []):
            field["value"] = format_value(field["value"], document)
        if "author" in ping_data:
            ping_data["author"]["name"] = format_value(ping_data["author"]["name"], document)
        if "thumbnail" in ping_data:
            ping_data["thumbnail"]["url"] = format_value(ping_data["thumbnail"]["url"], document)
        
        # Change the link back from the tiny url
        if temp_link is not None:
            document["link"] = temp_link

        return [process_scrapers(db, ping_data, document)]

    except Exception as error:
        logger.critical(msg=f"Couldn't create embed for ({document.get('product-name')}) on ({document.get('website')}) | {error}")



def process_scrapers(db, ping_data, document):
    try:
        # Lego-Retirement-Deals
        if (document.get("type") == "Lego-Retirement-Deals"):
            ping_data = lego_retirement_ping_data(db, ping_data, document) 

        return ping_data

    except Exception as error:
        logger.error(error)