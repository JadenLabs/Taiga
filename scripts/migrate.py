"""Script used to migrate sqlite3 json files to mongodb (FROM OLD-TAIGA)
Used from the project root
"""

import json
from src.database.database import database

FILE = "./tmp/user_items.json"
COLLECTION_NAME = "stats"
collection = database.db[COLLECTION_NAME]

with open(FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

for doc in data:
    del doc["createdAt"]
    del doc["updatedAt"]

    doc = {
        "_id": doc.get("id"),
        # "items": {"3": {"quantity": 1}},  # Users - give pebble doc
    }
    for key, value in doc.items():
        if key != "id":
            doc[key] = value

    collection.insert_one(doc)

print("Data import completed.")

# * For userItems migration
# for doc in data:
#     # Example doc
#     # {
#     #   "id":30,
#     #   "itemID":2,
#     #   "userID":1027380375028244551,
#     #   "createdAt":"2024-06-02 05:07:04.231 +00:00",
#     #   "updatedAt":"2024-06-02 18:13:32.506 +00:00",
#     #   "quantity":5
#     # }
#     print(doc)

#     del doc["createdAt"]
#     del doc["updatedAt"]

#     item_key = str(doc["itemID"])
#     item_value = {"quantity": doc["quantity"]}

#     database.users.update_one(
#         {"_id": str(doc["userID"])}, {"$set": {f"items.{item_key}": item_value}}
#     )
