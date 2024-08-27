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
        config_products_col =      os.getenv("COL_CONFIG_PRODUCTS")
        subscription_servers_col = os.getenv("COL_SUBSCRIPTION_SERVERS")
        ebay_col =                 os.getenv("COL_EBAY")
        retiring_sets_col =        os.getenv("COL_RETIRING_SETS")
        electronics_col =          os.getenv("COL_ELECTRONICS")

        # Connection
        conn_string = f"mongodb+srv://{username}:{password}@{db_deployment}.mongodb.net/"
        self.client = pymongo.MongoClient(conn_string)
        self.db = self.client[db_name]

        # Collections
        self.config_products_col =       self.db[config_products_col]
        self.subscription_servers_col =  self.db[subscription_servers_col]
        self.ebay_col =                  self.db[ebay_col]
        self.retiring_sets_col =         self.db[retiring_sets_col]
        self.electronics_col =           self.db[electronics_col]

        # Collections Dictionary
        self.collections = {
            config_products_col: self.config_products_col,
            subscription_servers_col: self.subscription_servers_col,
            ebay_col: self.ebay_col,
            retiring_sets_col: self.retiring_sets_col,
            electronics_col: self.electronics_col,
        }
        self.runtime_collections = {
            "ebay": self.ebay_col,
            "electronics": self.electronics_col,
            "retiring-sets": self.retiring_sets_col
        }


    def fetch_product(self, filter, col):
        return self.runtime_collections[col].find_one(filter)
    

    def get_user_webhooks(self, deal_type):
        subscription_name_doc = self.config_products_col.find_one({"deal-type": deal_type}, {"subscription-name-server": 1})
        if subscription_name_doc is None:
            logger.error(f"Deal type: \"{deal_type}\" not found")
        
        subscription_name = subscription_name_doc.get("subscription-name-server")
        if subscription_name is None:
            logger.error(f"Subscription name server not found in: \"{subscription_name_doc}\"")
        
        webhook_docs = self.subscription_servers_col.find({"subscription_name": subscription_name}, {"_id": 0, "webhooks": 1})

        webhooks = []
        for doc in webhook_docs:
            for webhook in doc.get("webhooks", {}).values():
                webhooks.append(webhook)

        return webhooks

    def __getitem__(self, col_name):
        return self.collections.get(col_name)