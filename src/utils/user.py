import traceback
from src.database.database import database
from src.core import logger

DEFAULT_USER = {
    "pets": 0,
    "lastPet": None,
    "beans": 0,
    "streak": 0,
}


def find_user_or_default(id: int | str, default_user: dict = DEFAULT_USER):
    try:
        id = str(id)
        user_doc = database.users.find_one({"_id": id})
        if user_doc is None:
            logger.debug(f"No doc for @{id}, creating")
            insert_doc = default_user
            insert_doc["_id"] = id
            database.users.insert_one(insert_doc)
            user_doc = database.users.find_one({"_id": id})

        return user_doc
    except Exception as e:
        traceback.print_exc()
        logger.error(f"An error has occured: ", e)
