import math
from enum import Enum
from src.core import core
from src.database.database import database


class SortOrder(Enum):
    """Enum for sort order"""

    Asc = 1
    """Ascending"""
    Desc = -1
    """Decending"""


class Leaderboard:
    def __init__(
        self,
        collection_name: str = None,
        items_list: list = None,
        page_size: int = core.config.data["leaderboards"]["default_page_size"],
        sort_field: str = None,
        sort_order: SortOrder = SortOrder.Asc,
        starting_page: int = 1,
    ):
        self.page_size = page_size
        self.items_list = items_list
        self.collection_name = collection_name
        self.sort_field = sort_field
        self.sort_order = sort_order

        self.items_count = (
            len(self.items_list)
            if self.items_list
            else database.db[self.collection_name].estimated_document_count()
        )
        self.page_count = math.ceil((self.items_count + 1) / page_size)

        self.page = starting_page

        assert (
            items_list or collection_name
        ), "Either a collection name or items list is required."

    def get_page(self, page: int = None):
        if page:
            self.page = page

        if self.collection_name:
            self.collection = database.db[self.collection_name]
            return self.get_slice_from_db(self.page)
        else:
            return self.get_slice_from_list(self.page)

    def get_slice_from_db(self, page: int):
        skip = (page - 1) * self.page_size
        limit = self.page_size

        sort_direction = self.sort_order.value

        cursor = (
            (
                self.collection.find().sort(self.sort_field, sort_direction)
                if self.sort_field
                else self.collection.find()
            )
            .skip(skip)
            .limit(limit)
        )

        items = list(cursor)
        ranked_items = []

        rank_offset = skip + 1

        for i, item in enumerate(items):
            ranked_item = {"rank": rank_offset + i, **item}
            ranked_items.append(ranked_item)

        return ranked_items

    def get_slice_from_list(self, page: int):
        if self.sort_field:
            reverse = self.sort_order == SortOrder.Desc
            self.items_list.sort(key=lambda x: x[self.sort_field], reverse=reverse)

        start = (page - 1) * self.page_size
        end = start + self.page_size

        items = self.items_list[start:end]
        ranked_items = []

        rank_offset = start + 1

        for i, item in enumerate(items):
            ranked_item = {"rank": rank_offset + i, **item}
            ranked_items.append(ranked_item)

        return ranked_items
