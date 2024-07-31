"""Script used to migrate sqlite3 json files to mongodb
Used from the project root
"""

import json
from src.database.database import database

FILE = "users.json"
COLLECTION_NAME = "users"
collection = database.db[COLLECTION_NAME]

with open(FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

for datum in data:
    del datum["createdAt"]
    del datum["updatedAt"]

    doc = {
        "_id": datum.get("id"),
    }
    for key, value in datum.items():
        if key != "id":
            doc[key] = value

    collection.insert_one(doc)

print("Data import completed.")
