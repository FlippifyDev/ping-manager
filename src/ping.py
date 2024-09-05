# Local Imports
from .scraper_handers import ping_data_electronics, ping_data_retiring_sets
from .exceptions import InvalidScraperType

# External Imports
from discord_webhook import DiscordWebhook
from dotenv import load_dotenv

import logging
import time
import json
import os
import re

load_dotenv()

logger = logging.getLogger("PING-MANAGER")




avatar_url = "https://i.imgur.com/oR6gpLI.png"
test_embeds = [
    {
        "title": "Your webhook works!!",
        "description": "If this is not the channel you want the pings to go to then simply re-enter another webhook. \nThe new webhook will replace the previous one.",
        "color": 65280
    }
]



def send_test_ping(change):
    try:
        webhook_url = list(change.values())
        if webhook_url == []:
            return
        
        webhook = DiscordWebhook(url=webhook_url[0], embeds=test_embeds, avatar_url=avatar_url, rate_limit_retry=True)
        webhook.execute()

    except Exception as error:
        logger.error(error)



def load_local_webhook(document):
    # Load the webhook from the config file
    env_webhook_name = document.get("type") + "-" + document.get("region").upper()
    webhook_url = os.getenv(env_webhook_name)
    if webhook_url is not None:
        return webhook_url
    
    env_webhook_name = document.get("type")
    webhook_url = os.getenv(env_webhook_name)
    if webhook_url is not None:
        return webhook_url
    

def send_ping(db, document):
    try:
        embed = create_embed(db, document)
        if embed == [None]:
            logger.warning(f"Embed not created for {document.get('product_name')} on {document.get('website')}")
            return

        webhook_url = load_local_webhook(document)
        if webhook_url == None:
            logger.critical(f"Scraper Type: {document.get('type')} has no webhook")
            return

        def send_to_webhook(webhook):
            webhook = DiscordWebhook(url=webhook, embeds=embed, avatar_url=avatar_url, rate_limit_retry=True)
            webhook.execute()

        send_to_webhook(webhook_url)
        user_webhooks = db.get_user_webhooks(document.get("type"))

        for user_webhook in user_webhooks:
            send_to_webhook(user_webhook)

        logger.info(f"Ping sent for {document.get('product_name')} on {document.get('website')}")

        time.sleep(0.5)

    except Exception as error:
        logger.critical(msg=f"Couldn't send ping for ({document.get('product_name')}) on ({document.get('link')}) | {error}")



def fetch_scraper_config(scraper_type):
    with open("config.json", "r", encoding="utf-8") as file:
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
        if document.get("type") != "Electronics":
            formatted_value = formatted_value.encode('latin1', errors='ignore').decode('utf-8', errors='ignore')

        return formatted_value
    return value



def create_embed(db, document):
    try:
        scraper_config = fetch_scraper_config(document.get("type"))

        # Create the dictionary with the extracted and formatted data
        ping_data = {key: format_value(value, document) for key, value in scraper_config.items()}

        # Handle nested fields and format them as well
        for field in ping_data.get("fields", []):
            field["value"] = format_value(field["value"], document)
        if "author" in ping_data:
            ping_data["author"]["name"] = format_value(ping_data["author"]["name"], document)
        if "thumbnail" in ping_data:
            ping_data["thumbnail"]["url"] = format_value(ping_data["thumbnail"]["url"], document)
        
        return [process_scrapers(db, ping_data, document)]

    except Exception as error:
        logger.critical(msg=f"Couldn't create embed for ({document.get('product-name')}) on ({document.get('website')}) | {error}")


def process_scrapers(db, ping_data, document):
    try:

        if (document.get("type") == "Electronics"):
            ping_data = ping_data_electronics(db, ping_data, document) 
        elif (document.get("type") == "Retiring-Sets-Deals"):
            ping_data = ping_data_retiring_sets(db, ping_data, document) 

        return ping_data

    except Exception as error:
        logger.error(error)