from dotenv import load_dotenv

import pymongo
import os


load_dotenv()


class Database():
    def __init__(self) -> None:
        # Config
        db_deployment =  os.getenv("DB_DEPLOYMENT")
        db_name =        os.getenv("DB_NAME")
        username =       os.getenv("DB_USERNAME")
        password =       os.getenv("DB_PASSWORD")

        # Config - Collections Names
        lego_retirement_col =  os.getenv("LEGO_RETIREMENT_COL")
        config_products_col =  os.getenv("CONFIG_PRODUCTS_COL")

        # Connection
        conn_string = f"mongodb+srv://{username}:{password}@{db_deployment}.mongodb.net/"
        self.client = pymongo.MongoClient(conn_string)
        self.db = self.client[db_name]

        # Collections
        self.lego_retirement_col = self.db[lego_retirement_col]
        self.config_products_col = self.db[config_products_col]

        # Collections Dictionary
        self.collections = {
            lego_retirement_col: self.lego_retirement_col,
            config_products_col: self.config_products_col
        }



    def fetch_product(self, filter):
        return self.lego_retirement_col.find_one(filter)



    def get_channel_id(self, scraper_type):
        # Fetching the discord channel id associated with each type of deal to know where to post deals.
        scraper = self.config_products_col.find_one({'scraper-type': scraper_type})
        if scraper:
            print(f"Fetched Channel ID for {scraper_type}: {scraper['channel-id']}")
            return scraper['channel-id']
        return None
        


    def __getitem__(self, col_name):
        return self.collections.get(col_name)