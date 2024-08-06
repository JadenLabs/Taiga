import os
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from src.core import logger


class Database:
    def __init__(self, mongo_uri: str) -> None:
        logger.debug("Attempting database connection")
        try:
            self.client = MongoClient(mongo_uri, server_api=ServerApi("1"))
            self.db = self.client["main"]
            logger.debug("Database connection successful")
        except Exception as err:
            logger.error(f"An error occured when connecting to the database: {err}")
            raise err

        # TODO, code smell, make more dynamic later
        self.items = self.db.items
        self.shop = self.db.shop
        self.staff = self.db.staff
        self.stats = self.db.stats
        self.users = self.db.users
        self.user_items = self.db.user_items


MONGO_URI = os.getenv("MONGO_URI")
database = Database(MONGO_URI)
