from src.database.database import database

COLLECTION_NAME = ""
collection = database.db[COLLECTION_NAME]

collection.update_many({}, {"$set": {}})
