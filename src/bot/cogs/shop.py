import random
from datetime import datetime, timezone
from discord import app_commands, Interaction, Embed, SelectOption, ButtonStyle
from discord.ext.commands import Cog
from discord.ui import Select, View, Button
from pymongo import ReturnDocument
from src.core import core
from src.bot import Bot
from src.database.database import database
from src.utils.user import find_user_or_default

MIN_COOLDOWN = 3600  # 1 hour floor regardless of items
SELL_RATE = 0.8

CATEGORY_ORDER = [
    ("boosts", "Boosts"),
    ("generators", "Generators"),
    ("consumables", "Consumables"),
    ("cosmetics", "Cosmetics"),
]


class Item:
    def __init__(self, data: dict):
        self.name: str = data["name"]
        self.description: str = data["description"]
        self.cost: int = data["cost"]
        self.ownership_limit: int = data.get("ownership_limit", 0)
        self.emoji: str = data.get("emoji", "🔹")
        self.cooldown_reduction: int = data.get("cooldown_reduction", 0)
        self.category: str = data.get("category", "boosts")
        self.beans_per_hour: int = data.get("beans_per_hour", 0)
        self.price_growth: float = data.get("price_growth", 1.0)
        self.bean_bonus: float = data.get("bean_bonus", 0.0)

    def cost_for(self, owned: int) -> int:
        """Current price given how many the user already owns."""
        if self.price_growth > 1.0:
            return round(self.cost * self.price_growth**owned)
        return self.cost

    def sell_value_for(self, owned: int) -> int:
        """Refund for selling one item while owning `owned` of them —
        SELL_RATE of the price that was paid for the most recent one."""
        return int(self.cost_for(max(owned - 1, 0)) * SELL_RATE)

    def fmt_name(self) -> str:
        return self.name.replace("_", " ").title()

    def fmt_shop_item(self, owned: int = 0) -> str:
        notes = []
        if self.cooldown_reduction > 0:
            mins = self.cooldown_reduction // 60
            notes.append(
                f"−{mins}min cooldown each" if self.ownership_limit != 1 else f"−{mins}min cooldown"
            )
        if self.beans_per_hour > 0:
            notes.append(f"+{self.beans_per_hour:,}/hr each")
        if self.bean_bonus > 0:
            notes.append(f"+{self.bean_bonus:.0%} beans each")
        if self.ownership_limit > 0:
            notes.append(f"owned {owned}/{self.ownership_limit}")
        elif owned > 0:
            notes.append(f"owned {owned}")
        subtext = " · ".join(notes)
        price = self.cost_for(owned)
        price_str = f"`{price:,}` beans"
        if self.price_growth > 1.0 and owned > 0:
            price_str = f"`{price:,}` beans (next)"
        return (
            f"{self.emoji} **{self.fmt_name()}** — {price_str}\n"
            f"-# {self.description}" + (f" · {subtext}" if subtext else "")
        )


SHOP_INVENTORY: list[Item] = [
    Item(data) for data in core.config.data["shop"]["items"]
]

ITEM_MAP: dict[str, Item] = {item.name: item for item in SHOP_INVENTORY}

SHOP_PAGES: list[tuple[str, list[Item]]] = [
    (title, items)
    for key, title in CATEGORY_ORDER
    if (items := [i for i in SHOP_INVENTORY if i.category == key])
]


def get_cooldown_reduction(inventory: dict) -> int:
    """Returns total cooldown reduction in seconds from owned items."""
    return sum(
        inventory.get(item.name, 0) * item.cooldown_reduction
        for item in SHOP_INVENTORY
    )


def get_bean_multiplier(user_doc: dict) -> float:
    """Global bean multiplier from golden beans (prestige) and bonus items.
    Applies to pets, /collect, and /fish."""
    prestige_bonus = core.config.data["prestige"]["bonus"]
    multiplier = 1.0 + prestige_bonus * user_doc.get("goldenBeans", 0)
    inventory = user_doc.get("inventory", {})
    for item in SHOP_INVENTORY:
        if item.bean_bonus > 0:
            multiplier *= 1.0 + item.bean_bonus * inventory.get(item.name, 0)
    return multiplier


def get_generator_rate(inventory: dict) -> int:
    """Total passive beans per hour from owned generators."""
    return sum(
        inventory.get(item.name, 0) * item.beans_per_hour
        for item in SHOP_INVENTORY
    )


def attempt_purchase(user_id: int, item: Item) -> tuple[dict | None, int, str | None]:
    """Atomically buys one item at its current scaled price.
    Returns (updated_doc, price_paid, error_message)."""
    user_doc = find_user_or_default(user_id)
    owned = user_doc.get("inventory", {}).get(item.name, 0)
    price = item.cost_for(owned)

    query = {"_id": str(user_id), "beans": {"$gte": price}}
    if item.ownership_limit > 0:
        # $not matches both missing fields and counts below the limit
        query[f"inventory.{item.name}"] = {"$not": {"$gte": item.ownership_limit}}
    if item.price_growth > 1.0:
        # Price depends on the owned count, so require it to be unchanged
        query[f"inventory.{item.name}"] = (
            owned if owned > 0 else {"$not": {"$gte": 1}}
        )

    update = {"$inc": {f"inventory.{item.name}": 1, "beans": -price}}
    if item.beans_per_hour > 0 and user_doc.get("lastCollect") is None:
        # First generator starts the income clock now
        update["$set"] = {"lastCollect": datetime.now(timezone.utc)}

    doc = database.users.find_one_and_update(
        query, update, return_document=ReturnDocument.AFTER
    )
    if doc is not None:
        return doc, price, None

    user_doc = find_user_or_default(user_id)
    owned = user_doc.get("inventory", {}).get(item.name, 0)
    if item.ownership_limit > 0 and owned >= item.ownership_limit:
        return None, price, (
            f"You already own the maximum of **{item.fmt_name()}** "
            f"({item.ownership_limit})."
        )
    beans_emoji = core.config.data["emojis"]["beans"]
    if user_doc.get("beans", 0) < item.cost_for(owned):
        return None, price, (
            f"Not enough beans. You need {beans_emoji} `{item.cost_for(owned):,}` "
            f"but only have `{user_doc.get('beans', 0):,}`."
        )
    return None, price, "The shop was busy — try that again."


def attempt_sell(user_id: int, item: Item) -> tuple[dict | None, int, str | None]:
    """Atomically sells one item for SELL_RATE of the price paid for it.
    Returns (updated_doc, refund, error_message)."""
    user_doc = find_user_or_default(user_id)
    owned = user_doc.get("inventory", {}).get(item.name, 0)
    if owned < 1:
        return None, 0, f"You don't own any **{item.fmt_name()}**."

    refund = item.sell_value_for(owned)
    doc = database.users.find_one_and_update(
        # Refund depends on the owned count, so require it to be unchanged
        {"_id": str(user_id), f"inventory.{item.name}": owned},
        {"$inc": {f"inventory.{item.name}": -1, "beans": refund}},
        return_document=ReturnDocument.AFTER,
    )
    if doc is None:
        return None, 0, "The shop was busy — try that again."
    return doc, refund, None


def build_shop_embed(user_doc: dict, page: int, action: str | None = None) -> Embed:
    inventory = user_doc.get("inventory", {})
    beans = user_doc.get("beans", 0)
    beans_emoji = core.config.data["emojis"]["beans"]
    page_title, page_items = SHOP_PAGES[page]

    items = "\n".join(
        item.fmt_shop_item(owned=inventory.get(item.name, 0))
        for item in page_items
    )
    description = f"{beans_emoji} Your beans: `{beans:,}`\n\n{items}"
    if action:
        description += f"\n\n{action}"

    embed = Embed(
        color=core.config.data["colors"]["primary"],
        title=f"{core.config.data['bot']['name']} Shop — {page_title}",
        description=description,
    )
    embed.set_footer(
        text=f"Page {page + 1}/{len(SHOP_PAGES)} · Items sell back for {SELL_RATE:.0%} of what you paid"
    )
    return embed


class BuySelect(Select):
    def __init__(self, page_items: list[Item], inventory: dict):
        options = []
        for item in page_items:
            owned = inventory.get(item.name, 0)
            at_limit = item.ownership_limit > 0 and owned >= item.ownership_limit
            options.append(
                SelectOption(
                    label=f"{item.fmt_name()} — {item.cost_for(owned):,} beans",
                    value=item.name,
                    emoji=item.emoji,
                    description="Owned limit reached" if at_limit else item.description[:100],
                )
            )
        super().__init__(placeholder="Buy an item...", options=options)

    async def callback(self, interaction: Interaction):
        item = ITEM_MAP[self.values[0]]
        doc, price, error = attempt_purchase(interaction.user.id, item)
        if error:
            embed = Embed(color=core.config.data["colors"]["error"], description=error)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        action = f"✅ Bought {item.emoji} **{item.fmt_name()}** for `{price:,}` beans."
        await self.view.refresh(interaction, doc, action)


class SellSelect(Select):
    def __init__(self, inventory: dict):
        options = []
        for item in SHOP_INVENTORY:
            owned = inventory.get(item.name, 0)
            if owned > 0:
                options.append(
                    SelectOption(
                        label=f"{item.fmt_name()} — sell for {item.sell_value_for(owned):,} beans",
                        value=item.name,
                        emoji=item.emoji,
                        description=f"You own {owned}",
                    )
                )
        if options:
            super().__init__(placeholder="Sell an item...", options=options[:25])
        else:
            super().__init__(
                placeholder="Nothing to sell yet",
                options=[SelectOption(label="-", value="-")],
                disabled=True,
            )

    async def callback(self, interaction: Interaction):
        item = ITEM_MAP[self.values[0]]
        doc, refund, error = attempt_sell(interaction.user.id, item)
        if error:
            embed = Embed(color=core.config.data["colors"]["error"], description=error)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        action = f"💰 Sold {item.emoji} **{item.fmt_name()}** for `{refund:,}` beans."
        await self.view.refresh(interaction, doc, action)


class PageButton(Button):
    def __init__(self, label: str, delta: int, disabled: bool):
        super().__init__(label=label, style=ButtonStyle.primary, disabled=disabled, row=2)
        self.delta = delta

    async def callback(self, interaction: Interaction):
        user_doc = find_user_or_default(interaction.user.id)
        await self.view.refresh(interaction, user_doc, None, page_delta=self.delta)


class ShopView(View):
    def __init__(self, user_id: int, user_doc: dict, page: int = 0):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.page = page
        self.message = None
        inventory = user_doc.get("inventory", {})
        self.add_item(BuySelect(SHOP_PAGES[page][1], inventory))
        self.add_item(SellSelect(inventory))
        self.add_item(PageButton("◀ Previous", -1, disabled=page <= 0))
        self.add_item(PageButton("Next ▶", 1, disabled=page >= len(SHOP_PAGES) - 1))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="This isn't your shop! Open your own with `/shop`.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def refresh(
        self,
        interaction: Interaction,
        user_doc: dict,
        action: str | None,
        page_delta: int = 0,
    ):
        """Rebuilds the embed and components after a transaction or page turn."""
        new_page = max(0, min(self.page + page_delta, len(SHOP_PAGES) - 1))
        new_view = ShopView(self.user_id, user_doc, new_page)
        new_view.message = self.message
        self.stop()
        await interaction.response.edit_message(
            embed=build_shop_embed(user_doc, new_page, action), view=new_view
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class Shop(Cog):
    """Shop cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Open the shop")
    async def shop(self, ctx: Interaction):
        user_doc = find_user_or_default(ctx.user.id)
        view = ShopView(ctx.user.id, user_doc)
        await ctx.response.send_message(embed=build_shop_embed(user_doc, 0), view=view)
        view.message = await ctx.original_response()

    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item="The item to purchase")
    @app_commands.choices(
        item=[
            app_commands.Choice(name=f"{i.emoji} {i.fmt_name()}", value=i.name)
            for i in SHOP_INVENTORY
        ]
    )
    async def buy(self, ctx: Interaction, item: app_commands.Choice[str]):
        shop_item = ITEM_MAP[item.value]
        doc, price, error = attempt_purchase(ctx.user.id, shop_item)
        if error:
            embed = Embed(color=core.config.data["colors"]["error"], description=error)
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        beans_emoji = core.config.data["emojis"]["beans"]
        owned = doc.get("inventory", {}).get(shop_item.name, 0)
        owned_str = (
            f"**{owned}** / {shop_item.ownership_limit}"
            if shop_item.ownership_limit > 0
            else f"**{owned}**"
        )
        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{shop_item.emoji} {shop_item.fmt_name()}",
            description=(
                f"Bought for {beans_emoji} `{price:,}` beans.\n"
                f"Owned: {owned_str} · `{doc.get('beans', 0):,}` remaining"
            ),
        )
        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="sell", description="Sell an item back for 80% of what you paid")
    @app_commands.describe(item="The item to sell")
    @app_commands.choices(
        item=[
            app_commands.Choice(name=f"{i.emoji} {i.fmt_name()}", value=i.name)
            for i in SHOP_INVENTORY
        ]
    )
    async def sell(self, ctx: Interaction, item: app_commands.Choice[str]):
        shop_item = ITEM_MAP[item.value]
        doc, refund, error = attempt_sell(ctx.user.id, shop_item)
        if error:
            embed = Embed(color=core.config.data["colors"]["error"], description=error)
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        beans_emoji = core.config.data["emojis"]["beans"]
        owned = doc.get("inventory", {}).get(shop_item.name, 0)
        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{shop_item.emoji} {shop_item.fmt_name()}",
            description=(
                f"Sold for {beans_emoji} `{refund:,}` beans.\n"
                f"Owned: **{owned}** · {beans_emoji} `{doc.get('beans', 0):,}` total"
            ),
        )
        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="open", description="Open a mystery box")
    async def open(self, ctx: Interaction):
        box = ITEM_MAP["mystery_box"]
        beans_emoji = core.config.data["emojis"]["beans"]

        # Consume one box atomically
        doc = database.users.find_one_and_update(
            {"_id": str(ctx.user.id), "inventory.mystery_box": {"$gte": 1}},
            {"$inc": {"inventory.mystery_box": -1}},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description=f"You don't have any {box.emoji} **Mystery Boxes**. Grab one in `/shop`!",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        roll = random.random()
        if roll < 0.10:  # jackpot
            amount = random.randint(150000, 300000)
            database.users.update_one(
                {"_id": str(ctx.user.id)}, {"$inc": {"beans": amount}}
            )
            result = f"💎 **JACKPOT!** {beans_emoji} `+{amount:,}` beans!"
        elif roll < 0.40:  # random item
            inventory = doc.get("inventory", {})
            eligible = [
                i for i in SHOP_INVENTORY
                if i.category in ("boosts", "consumables")
                and i.name != "mystery_box"
                and (i.ownership_limit == 0 or inventory.get(i.name, 0) < i.ownership_limit)
            ]
            if eligible:
                prize = random.choice(eligible)
                database.users.update_one(
                    {"_id": str(ctx.user.id)},
                    {"$inc": {f"inventory.{prize.name}": 1}},
                )
                result = f"You found {prize.emoji} **{prize.fmt_name()}**!"
            else:
                amount = random.randint(20000, 50000)
                database.users.update_one(
                    {"_id": str(ctx.user.id)}, {"$inc": {"beans": amount}}
                )
                result = f"{beans_emoji} `+{amount:,}` beans!"
        else:  # beans
            amount = random.randint(10000, 40000)
            database.users.update_one(
                {"_id": str(ctx.user.id)}, {"$inc": {"beans": amount}}
            )
            result = f"{beans_emoji} `+{amount:,}` beans!"

        remaining = doc.get("inventory", {}).get("mystery_box", 0)
        embed = Embed(
            color=core.config.data["colors"]["secondary"],
            title=f"{box.emoji} Mystery Box opened!",
            description=f"{result}\n-# Boxes left: {remaining}",
        )
        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="inventory", description="View your items")
    async def inventory(self, ctx: Interaction):
        user_doc = find_user_or_default(ctx.user.id)
        inventory = user_doc.get("inventory", {})

        owned_items = [
            f"{item.emoji} **{item.fmt_name()}** ×{count}"
            for item in SHOP_INVENTORY
            if (count := inventory.get(item.name, 0)) > 0
        ]

        base_cooldown = core.config.data["cooldowns"]["pet"]
        reduction = get_cooldown_reduction(inventory)
        effective = max(base_cooldown - reduction, MIN_COOLDOWN)

        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{ctx.user.display_name}'s Inventory",
            description="\n".join(owned_items) if owned_items else "No items yet. Check out `/shop`!",
        )
        cooldown_value = f"**{effective / 3600:.1f}hrs**"
        if reduction > 0:
            cooldown_value += f" (−{reduction // 60}min from items)"
        embed.add_field(name="Pet Cooldown", value=cooldown_value, inline=False)

        rate = get_generator_rate(inventory)
        if rate > 0:
            embed.add_field(
                name="Generators",
                value=f"**{rate:,}** beans/hr — claim with `/collect`",
                inline=False,
            )

        multiplier = get_bean_multiplier(user_doc)
        if multiplier > 1.0:
            embed.add_field(
                name="Bean Multiplier",
                value=f"**×{multiplier:.2f}** (applies to pets, /collect, /fish)",
                inline=False,
            )

        await ctx.response.send_message(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Shop(bot))
