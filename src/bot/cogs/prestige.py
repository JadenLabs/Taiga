import math
from discord import app_commands, Interaction, Embed, ButtonStyle
from discord.ext.commands import Cog
from discord.ui import View, Button
from pymongo import ReturnDocument
from src.core import core
from src.bot import Bot
from src.database.database import database
from src.utils.user import find_user_or_default
from src.bot.cogs.shop import (
    SHOP_INVENTORY,
    get_bean_multiplier,
    get_head_start_fraction,
    check_achievements,
    format_unlocks,
)


def prestige_payout(beans: int) -> int:
    """Golden beans earned for prestiging with `beans` banked.
    floor(sqrt(beans / base_cost)) - diminishing returns, so hoarding before
    prestiging pays off but each bean is worth steadily less."""
    base_cost = core.config.data["prestige"]["base_cost"]
    if beans < base_cost:
        return 0
    # isqrt stays exact for very large bean counts (no float rounding)
    return math.isqrt(beans // base_cost)


def kept_cosmetics(inventory: dict) -> dict:
    """Cosmetic items survive prestige."""
    return {
        item.name: count
        for item in SHOP_INVENTORY
        if item.category == "cosmetics" and (count := inventory.get(item.name, 0)) > 0
    }


class PrestigeConfirmView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.message = None

        button = Button(
            label="Use a life - prestige!", style=ButtonStyle.danger, emoji="🐱"
        )
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
        beans = user_doc.get("beans", 0)
        payout = prestige_payout(beans)
        if payout < 1:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="You no longer have enough beans to prestige. Run `/prestige` again.",
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        cosmetics = kept_cosmetics(user_doc.get("inventory", {}))
        kept_beans = int(beans * get_head_start_fraction(user_doc))

        # Guard on the exact bean balance so a double-click can't prestige twice
        doc = database.users.find_one_and_update(
            {"_id": str(self.user_id), "beans": beans},
            {
                "$set": {
                    "beans": kept_beans,
                    "inventory": cosmetics,
                    "lastCollect": None,
                    "generatorRate": 0,
                },
                "$inc": {"goldenBeans": payout, "prestiges": 1},
            },
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="Prestige failed - your beans changed. Run `/prestige` again.",
            )
            return await interaction.response.edit_message(embed=embed, view=None)

        self.stop()
        unlocked = check_achievements(self.user_id)
        golden_emoji = core.config.data["emojis"]["golden_beans"]
        beans_emoji = core.config.data["emojis"]["beans"]
        multiplier = get_bean_multiplier(doc)
        kept_line = (
            f"\n{beans_emoji} Head Start kept `{kept_beans:,}` beans"
            if kept_beans > 0
            else ""
        )
        embed = Embed(
            color=core.config.data["colors"]["secondary"],
            title="🐱 A new life begins!",
            description=(
                f"{core.config.data['bot']['name']} grants you {golden_emoji} **+{payout}** golden beans.\n\n"
                f"{golden_emoji} Golden beans: **{doc.get('goldenBeans', 0)}**\n"
                f"✨ Current multiplier: **×{multiplier:.2f}**"
                f"{kept_line}\n\n"
                f"-# Spend golden beans on permanent upgrades with `/upgrades`.\n"
                f"-# Your beans and items were reset. Cosmetics, pets, streaks, and upgrades were kept."
                f"{format_unlocks(unlocked)}"
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
        description="Spend one of Taiga's nine lives to convert your beans into golden beans",
    )
    async def prestige(self, ctx: Interaction):
        user_doc = find_user_or_default(ctx.user.id)
        beans = user_doc.get("beans", 0)
        golden_beans = user_doc.get("goldenBeans", 0)
        base_cost = core.config.data["prestige"]["base_cost"]
        payout = prestige_payout(beans)

        beans_emoji = core.config.data["emojis"]["beans"]
        golden_emoji = core.config.data["emojis"]["golden_beans"]
        multiplier = get_bean_multiplier(user_doc)

        description = (
            f"Trade your beans for {golden_emoji} **golden beans** - the prestige "
            f"currency you spend on permanent upgrades in `/upgrades`.\n\n"
            f"{golden_emoji} Golden beans: **{golden_beans}** (×{multiplier:.2f} multiplier)\n"
            f"{beans_emoji} You have: `{beans:,}` beans\n"
            f"{golden_emoji} Prestiging now earns: **+{payout}**\n\n"
            f"**Resets:** beans, generators, and all bean-bought items\n"
            f"**Keeps:** pets, streaks, cosmetics, golden beans, permanent upgrades"
        )

        if payout < 1:
            needed = base_cost - beans
            embed = Embed(
                color=core.config.data["colors"]["primary"],
                title="🐱 Nine Lives",
                description=description
                + f"\n\nYou need `{needed:,}` more beans to earn your first golden bean.",
            )
            return await ctx.response.send_message(embed=embed)

        embed = Embed(
            color=core.config.data["colors"]["secondary"],
            title="🐱 Nine Lives - ready!",
            description=description + "\n\n**This cannot be undone.**",
        )
        view = PrestigeConfirmView(ctx.user.id)
        await ctx.response.send_message(embed=embed, view=view)
        view.message = await ctx.original_response()


async def setup(bot: Bot):
    await bot.add_cog(Prestige(bot))
