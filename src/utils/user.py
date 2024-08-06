from src.database.database import database
from src.core import logger

DEFAULT_USER = {
    "pets": 0,
    "lastPet": None,
    "beans": 0,
}


def find_user_or_default(id: int, default_user: dict = DEFAULT_USER):
    user_doc = database.users.find_one({"_id": str(id)})
    if user_doc is None:
        logger.debug(f"No doc for @{id}, creating")
        insert_doc = default_user
        insert_doc["_id"] = id
        database.users.insert_one(insert_doc)
        user_doc = database.users.find_one({"_id": id})

    return user_doc
