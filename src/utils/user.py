import traceback
from src.core import core
from datetime import datetime, timezone, timedelta
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

def get_time_last_pet(user_doc: dict):
    last_pet = user_doc.get("lastPet")
    if last_pet is None:
        return None

    date_format = "%Y-%m-%d %H:%M:%S.%f %z"
    time_last_pet: datetime = (
        datetime.strptime(last_pet, date_format)
        if isinstance(last_pet, str)
        else last_pet
    )
    if time_last_pet.tzinfo is None:
        time_last_pet = time_last_pet.replace(tzinfo=timezone.utc)

    return time_last_pet

def get_pet_cooldown_over(time_last_pet: datetime):
    pet_cooldown = core.config.data["cooldowns"]["pet"]
    cooldown_over = time_last_pet + timedelta(seconds=pet_cooldown)
    return cooldown_over

def get_pet_cooldown_over_ts(cooldown_over: datetime):
    return f"<t:{int(cooldown_over.timestamp())}:R>"