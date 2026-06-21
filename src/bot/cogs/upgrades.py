from discord import app_commands, Interaction, Embed, SelectOption, ButtonStyle
from discord.ext.commands import Cog
from discord.ui import Select, View
from pymongo import ReturnDocument
from src.core import core
from src.bot import Bot
from src.database.database import database
from src.utils.user import find_user_or_default
from src.bot.cogs.shop import (
    PERMANENT_UPGRADES,
    PERMANENT_MAP,
    PermanentUpgrade,
    get_permanent_level,
)


def effect_summary(upgrade: PermanentUpgrade) -> str:
    """Human-readable description of one level of an upgrade's effect."""
    v = upgrade.effect_value
    if upgrade.effect == "multiplier":
        return f"+{v:.0%} bean multiplier / level"
    if upgrade.effect == "collect_cap":
        return f"+{v:g}hrs storage / level"
    if upgrade.effect == "cooldown_floor":
        return f"−{int(v // 60)}min cooldown floor / level"
    if upgrade.effect == "auto_collect":
        return "generators never overflow"
    if upgrade.effect == "head_start":
        return f"keep +{v:.0%} beans on prestige / level"
    if upgrade.effect == "lucky":
        return f"+{v:.0%} luck / level"
    if upgrade.effect == "box_capacity":
        if upgrade.effect_growth:
            return (
                f"+{int(v)} box capacity / level "
                f"(+{upgrade.effect_growth:g} more each level)"
            )
        return f"+{int(v)} box capacity / level"
    return ""


def fmt_upgrade(upgrade: PermanentUpgrade, level: int) -> str:
    golden_emoji = core.config.data["emojis"]["golden_beans"]
    lvl_str = f"Lv.{level}" + (f"/{upgrade.max_level}" if upgrade.max_level else "")
    if upgrade.at_max(level):
        price_str = "**MAXED**"
    else:
        price_str = f"`{upgrade.cost_for(level):,}` {golden_emoji}"
    return (
        f"{upgrade.emoji} **{upgrade.fmt_name()}** - {price_str} · `{lvl_str}`\n"
        f"-# {upgrade.description} · {effect_summary(upgrade)}"
    )


def attempt_buy_upgrade(
    user_id: int, upgrade: PermanentUpgrade
) -> tuple[dict | None, int, str | None]:
    """Atomically buy one level of a permanent upgrade with golden beans."""
    user_doc = find_user_or_default(user_id)
    level = get_permanent_level(user_doc, upgrade.name)
    golden_emoji = core.config.data["emojis"]["golden_beans"]

    if upgrade.at_max(level):
        return None, 0, f"**{upgrade.fmt_name()}** is already at max level."

    cost = upgrade.cost_for(level)
    query = {
        "_id": str(user_id),
        "goldenBeans": {"$gte": cost},
        # Level must be unchanged so the price we charge matches what we read
        f"permanentUpgrades.{upgrade.name}": (
            level if level > 0 else {"$not": {"$gte": 1}}
        ),
    }
    doc = database.users.find_one_and_update(
        query,
        {
            "$inc": {
                "goldenBeans": -cost,
                f"permanentUpgrades.{upgrade.name}": 1,
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    if doc is not None:
        return doc, cost, None

    user_doc = find_user_or_default(user_id)
    if user_doc.get("goldenBeans", 0) < cost:
        return (
            None,
            cost,
            (
                f"Not enough golden beans. You need {golden_emoji} `{cost:,}` "
                f"but only have `{user_doc.get('goldenBeans', 0):,}`. Earn more with `/prestige`."
            ),
        )
    return None, cost, "Something changed - try that again."


def build_upgrades_embed(user_doc: dict, action: str | None = None) -> Embed:
    golden_emoji = core.config.data["emojis"]["golden_beans"]
    golden = user_doc.get("goldenBeans", 0)
    lines = "\n".join(
        fmt_upgrade(u, get_permanent_level(user_doc, u.name))
        for u in PERMANENT_UPGRADES
    )
    description = f"{golden_emoji} Your golden beans: `{golden:,}`\n\n{lines}"
    if action:
        description += f"\n\n{action}"
    embed = Embed(
        color=core.config.data["colors"]["secondary"],
        title="🐾 Permanent Upgrades",
        description=description,
    )
    embed.set_footer(text="Bought with golden beans · These survive prestige")
    return embed


class UpgradeSelect(Select):
    def __init__(self, user_doc: dict):
        options = []
        for u in PERMANENT_UPGRADES:
            level = get_permanent_level(user_doc, u.name)
            maxed = u.at_max(level)
            label = f"{u.fmt_name()} - " + (
                "MAXED" if maxed else f"{u.cost_for(level):,} golden"
            )
            options.append(
                SelectOption(
                    label=label,
                    value=u.name,
                    emoji=u.emoji,
                    description=effect_summary(u)[:100],
                )
            )
        super().__init__(placeholder="Buy an upgrade...", options=options[:25])

    async def callback(self, interaction: Interaction):
        upgrade = PERMANENT_MAP[self.values[0]]
        doc, cost, error = attempt_buy_upgrade(interaction.user.id, upgrade)
        if error:
            embed = Embed(color=core.config.data["colors"]["error"], description=error)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        golden_emoji = core.config.data["emojis"]["golden_beans"]
        action = f"✅ Bought {upgrade.emoji} **{upgrade.fmt_name()}** for `{cost:,}` {golden_emoji}."
        await self.view.refresh(interaction, doc, action)


class UpgradesView(View):
    def __init__(self, user_id: int, user_doc: dict):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.message = None
        self.add_item(UpgradeSelect(user_doc))

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="This isn't your menu! Open your own with `/upgrades`.",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def refresh(
        self, interaction: Interaction, user_doc: dict, action: str | None
    ):
        new_view = UpgradesView(self.user_id, user_doc)
        new_view.message = self.message
        self.stop()
        await interaction.response.edit_message(
            embed=build_upgrades_embed(user_doc, action), view=new_view
        )

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message is not None:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class Upgrades(Cog):
    """Permanent (golden bean) upgrade shop"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(
        name="upgrades", description="Spend golden beans on permanent upgrades"
    )
    async def upgrades(self, ctx: Interaction):
        user_doc = find_user_or_default(ctx.user.id)
        view = UpgradesView(ctx.user.id, user_doc)
        await ctx.response.send_message(embed=build_upgrades_embed(user_doc), view=view)
        view.message = await ctx.original_response()


async def setup(bot: Bot):
    await bot.add_cog(Upgrades(bot))
