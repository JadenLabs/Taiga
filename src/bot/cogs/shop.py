from discord import app_commands, Interaction, Embed
from discord.ext.commands import Cog
from src.core import core
from src.bot import Bot


class Item:
    def __init__(
        self,
        name: str,
        description: str,
        cost: int | None = None,
        ownership_limit: int = 0,
    ):
        self.name = name
        self.description = description
        self.cost = cost
        self.ownership_limit = ownership_limit

    def fmt_name(self) -> str:
        return self.name.replace("_", " ").title()

    def fmt_shop_item(self) -> str:
        fmt_max_items = f" (max: {self.ownership_limit})" if self.ownership_limit > 0 else ""
        return f"`{self.cost}` - {self.fmt_name()}\n-# {self.description}{fmt_max_items}"


class Items:
    alarm_clock = Item(
        "alarm_clock",
        f"Reminds you when {core.config.data['bot']['name']} can be pet.",
        cost=50_000,
        ownership_limit=1,
    )

    cat_toy = Item(
        "cat_toy",
        f"Decreases {core.config.data['bot']['name']}'s sleep duration by 1hr",
        cost=100_000,
        ownership_limit=8,
    )


SHOP_INVENTORY = [Items.alarm_clock, Items.cat_toy]


class Shop(Cog):
    """Shop cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Open the shop")
    async def shop(self, ctx: Interaction):
        """Open the shop"""
        shop_items = [
            f"{i}. {item.fmt_shop_item()}"
            for i, item in enumerate(SHOP_INVENTORY, start=1)
        ]

        page = "\n".join(shop_items)

        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{core.config.data['bot']['name']} Shop",
            description=f"{page}",
        )

        await ctx.response.send_message(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Shop(bot))
