from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ext.commands import Cog
from discord.ui import View, Button
from pymongo import ReturnDocument
from src.core import core
from src.bot import Bot
from src.database.database import database
from src.utils.user import find_user_or_default
from src.bot.cogs.shop import SHOP_INVENTORY, get_bean_multiplier


def next_prestige_cost(golden_beans: int) -> int:
    cfg = core.config.data["prestige"]
    return round(cfg["base_cost"] * cfg["cost_growth"] ** golden_beans)


def kept_cosmetics(inventory: dict) -> dict:
    """Cosmetic items survive prestige."""
    return {
        item.name: count
        for item in SHOP_INVENTORY
        if item.category == "cosmetics" and (count := inventory.get(item.name, 0)) > 0
    }


class PrestigeConfirmView(View):
    def __init__(self, user_id: int, golden_beans: int, cost: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.golden_beans = golden_beans
        self.cost = cost
        self.message = None

        button = Button(label="Use a life — prestige!", style=ButtonStyle.danger, emoji="🐱")
        button.callback = self.confirm
        self.add_item(button)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="This isn't your prestige! Use `/prestige` yourself.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def confirm(self, interaction: Interaction):
        user_doc = find_user_or_default(self.user_id)
        cosmetics = kept_cosmetics(user_doc.get("inventory", {}))

        # Guard on beans and goldenBeans so a double-click can't prestige twice
        query = {
            "_id": str(self.user_id),
            "beans": {"$gte": self.cost},
            "goldenBeans": {"$in": [self.golden_beans, None]}
            if self.golden_beans == 0
            else self.golden_beans,
        }
        doc = database.users.find_one_and_update(
            query,
            {
                "$set": {
                    "beans": 0,
                    "inventory": cosmetics,
                    "lastCollect": None,
                },
                "$inc": {"goldenBeans": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="Prestige failed — your beans or golden beans changed. Run `/prestige` again.",
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        self.stop()
        golden_emoji = core.config.data["emojis"]["golden_beans"]
        new_golden = doc.get("goldenBeans", 0)
        multiplier = get_bean_multiplier(doc)
        embed = Embed(
            color=core.config.data["colors"]["secondary"],
            title="🐱 A new life begins!",
            description=(
                f"{core.config.data['bot']['name']} grants you a golden bean.\n\n"
                f"{golden_emoji} Golden beans: **{new_golden}**\n"
                f"✨ Permanent bean multiplier: **×{multiplier:.2f}**\n\n"
                f"-# Your beans and items were reset. Cosmetics, pets, and streaks were kept."
            ),
        )
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class Prestige(Cog):
    """Prestige (Nine Lives) cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(
        name="prestige",
        description="Spend one of Taiga's nine lives for a permanent bean multiplier",
    )
    async def prestige(self, ctx: Interaction):
        user_doc = find_user_or_default(ctx.user.id)
        golden_beans = user_doc.get("goldenBeans", 0)
        beans = user_doc.get("beans", 0)
        cost = next_prestige_cost(golden_beans)
        bonus = core.config.data["prestige"]["bonus"]

        beans_emoji = core.config.data["emojis"]["beans"]
        golden_emoji = core.config.data["emojis"]["golden_beans"]
        multiplier = get_bean_multiplier(user_doc)

        description = (
            f"Trade everything for a {golden_emoji} **golden bean** — "
            f"a permanent **+{bonus:.0%}** bean multiplier.\n\n"
            f"{golden_emoji} Golden beans: **{golden_beans}** (×{multiplier:.2f} multiplier)\n"
            f"{beans_emoji} Next golden bean costs: `{cost:,}` beans\n"
            f"{beans_emoji} You have: `{beans:,}` beans\n\n"
            f"**Resets:** beans, all items (except cosmetics)\n"
            f"**Keeps:** pets, streaks, cosmetics, golden beans"
        )

        if beans < cost:
            embed = Embed(
                color=core.config.data["colors"]["primary"],
                title="🐱 Nine Lives",
                description=description
                + f"\n\nYou need `{cost - beans:,}` more beans to prestige.",
            )
            return await ctx.response.send_message(embed=embed)

        embed = Embed(
            color=core.config.data["colors"]["secondary"],
            title="🐱 Nine Lives — ready!",
            description=description + "\n\n**This cannot be undone.**",
        )
        view = PrestigeConfirmView(ctx.user.id, golden_beans, cost)
        await ctx.response.send_message(embed=embed, view=view)
        view.message = await ctx.original_response()


async def setup(bot: Bot):
    await bot.add_cog(Prestige(bot))
