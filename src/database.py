from dotenv import load_dotenv

import logging
import pymongo
import os

logger = logging.getLogger("PING-MANAGER")

load_dotenv()


class Database():
    def __init__(self) -> None:
        # Config
        db_deployment =  os.getenv("DB_DEPLOYMENT")
        db_name =        os.getenv("DB_NAME")
        username =       os.getenv("DB_USERNAME")
        password =       os.getenv("DB_PASSWORD")

        # Config - Collections Names
        lego_retirement_col =      os.getenv("LEGO_RETIREMENT_COL")
        config_products_col =      os.getenv("CONFIG_PRODUCTS_COL")
        subscription_servers_col = os.getenv("SUBSCRIPTION_SERVERS_COL")

        # Connection
        conn_string = f"mongodb+srv://{username}:{password}@{db_deployment}.mongodb.net/"
        self.client = pymongo.MongoClient(conn_string)
        self.db = self.client[db_name]

        # Collections
        self.lego_retirement_col = self.db[lego_retirement_col]
        self.config_products_col = self.db[config_products_col]
        self.subscription_servers_col = self.db[subscription_servers_col]

        # Collections Dictionary
        self.collections = {
            lego_retirement_col: self.lego_retirement_col,
            config_products_col: self.config_products_col,
            subscription_servers_col: self.subscription_servers_col
        }



    def fetch_product(self, filter):
        return self.lego_retirement_col.find_one(filter)



    def get_channel_id(self, scraper_type):
        # Fetching the discord channel id associated with each type of deal to know where to post deals.
        scraper = self.config_products_col.find_one({'scraper-type': scraper_type})
        if scraper:
            logger.info(f"Fetched Channel ID for {scraper_type}: {scraper['channel-id']}")
            return scraper['channel-id']
        return None
    

    def get_user_webhooks(self, deal_type):
        subscription_name_doc = self.config_products_col.find_one({"deal-type": deal_type}, {"subscription-name-server": 1})
        if subscription_name_doc is None:
            logger.error(f"Deal type: \"{deal_type}\" not found")
        
        subscription_name = subscription_name_doc.get("subscription-name-server")
        if subscription_name is None:
            logger.error(f"Subscription name server not found in: \"{subscription_name_doc}\"")
        
        webhook_docs = self.subscription_servers_col.find({"subscription_name": subscription_name}, {"webhook": 1})
        webhooks = [doc.get("webhook") for doc in webhook_docs if doc.get("webhook") is not None]

        return webhooks

    def __getitem__(self, col_name):
        return self.collections.get(col_name)