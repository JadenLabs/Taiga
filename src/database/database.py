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
            ping_res = self.db.command("ping")
            if ping_res.get("ok") != 1:
                raise Exception(
                    "Ping command failed, database connection not established"
                )
            logger.debug("Database connection successful")
        except Exception as err:
            logger.error(f"An error occured when connecting to the database: {err}")
            raise err

        # TODO, code smell, make more dynamic later
        self.items = self.db.items
        self.staff = self.db.staff
        self.stats = self.db.stats
        self.users = self.db.users


MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set")
database = Database(MONGO_URI)
