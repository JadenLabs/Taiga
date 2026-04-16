from discord import app_commands, Interaction, Embed
from discord.ext.commands import Cog
from src.core import core
from src.bot import Bot
from src.database.database import database
from src.utils.user import find_user_or_default

MIN_COOLDOWN = 3600  # 1 hour floor regardless of items


class Item:
    def __init__(self, data: dict):
        self.name: str = data["name"]
        self.description: str = data["description"]
        self.cost: int = data["cost"]
        self.ownership_limit: int = data.get("ownership_limit", 0)
        self.emoji: str = data.get("emoji", "🔹")
        self.cooldown_reduction: int = data.get("cooldown_reduction", 0)

    def fmt_name(self) -> str:
        return self.name.replace("_", " ").title()

    def fmt_shop_item(self) -> str:
        notes = []
        if self.cooldown_reduction > 0:
            mins = self.cooldown_reduction // 60
            notes.append(
                f"−{mins}min cooldown each" if self.ownership_limit != 1 else f"−{mins}min cooldown"
            )
        if self.ownership_limit > 0:
            notes.append(f"limit {self.ownership_limit}")
        subtext = " · ".join(notes)
        return (
            f"{self.emoji} **{self.fmt_name()}** — `{self.cost:,}` beans\n"
            f"-# {self.description}" + (f" · {subtext}" if subtext else "")
        )


SHOP_INVENTORY: list[Item] = [
    Item(data) for data in core.config.data["shop"]["items"]
]

ITEM_MAP: dict[str, Item] = {item.name: item for item in SHOP_INVENTORY}


def get_cooldown_reduction(inventory: dict) -> int:
    """Returns total cooldown reduction in seconds from owned items."""
    return sum(
        inventory.get(item.name, 0) * item.cooldown_reduction
        for item in SHOP_INVENTORY
    )


class Shop(Cog):
    """Shop cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Open the shop")
    async def shop(self, ctx: Interaction):
        items = "\n".join(item.fmt_shop_item() for item in SHOP_INVENTORY)

        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{core.config.data['bot']['name']} Shop",
            description=items,
        )
        embed.set_footer(text="/buy to purchase  ·  /inventory to view your items")

        await ctx.response.send_message(embed=embed)

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
        user_doc = find_user_or_default(ctx.user.id)
        inventory = user_doc.get("inventory", {})
        owned = inventory.get(shop_item.name, 0)
        beans = user_doc.get("beans", 0)
        beans_emoji = core.config.data["emojis"]["beans"]

        if shop_item.ownership_limit > 0 and owned >= shop_item.ownership_limit:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description=f"You already own the maximum of **{shop_item.fmt_name()}** ({shop_item.ownership_limit}).",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        if beans < shop_item.cost:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description=(
                    f"Not enough beans. You need {beans_emoji} `{shop_item.cost:,}` "
                    f"but only have `{beans:,}`."
                ),
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        new_beans = beans - shop_item.cost
        new_owned = owned + 1
        database.users.find_one_and_update(
            {"_id": str(ctx.user.id)},
            {
                "$inc": {f"inventory.{shop_item.name}": 1},
                "$set": {"beans": new_beans},
            },
        )

        owned_str = (
            f"**{new_owned}** / {shop_item.ownership_limit}"
            if shop_item.ownership_limit > 0
            else f"**{new_owned}**"
        )
        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{shop_item.emoji} {shop_item.fmt_name()}",
            description=(
                f"Owned: {owned_str}\n"
                f"{beans_emoji} `{new_beans:,}` remaining"
            ),
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

        await ctx.response.send_message(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Shop(bot))
