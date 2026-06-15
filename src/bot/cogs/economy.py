import os
import random
from datetime import datetime, timezone
from discord import app_commands, Interaction, Embed
from discord.ext.commands import Cog
from src.core import core
from src.bot import Bot
from src.database.database import database
from src.utils.user import find_user_or_default
from src.bot.cogs.shop import (
    get_bean_multiplier,
    get_generator_rate,
    get_collect_cap_hours,
    check_achievements,
    format_unlocks,
)


def parse_ts(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f %z")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


class Economy(Cog):
    """Passive income and minigames"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="collect", description="Collect beans from your generators")
    async def collect(self, ctx: Interaction):
        user_doc = find_user_or_default(ctx.user.id)
        inventory = user_doc.get("inventory", {})
        beans_emoji = core.config.data["emojis"]["beans"]

        rate = get_generator_rate(inventory)
        if rate == 0:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="You don't own any generators yet. Grab a 🌱 **Bean Sprout** in `/shop`!",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        now = datetime.now(timezone.utc)
        last_collect = parse_ts(user_doc.get("lastCollect"))
        if last_collect is None:
            # Generators owned before lastCollect existed — start the clock now
            database.users.update_one(
                {"_id": str(ctx.user.id)}, {"$set": {"lastCollect": now}}
            )
            embed = Embed(
                color=core.config.data["colors"]["primary"],
                description="Your generators are now running! Come back soon to `/collect`.",
            )
            return await ctx.response.send_message(embed=embed)

        cap_hours = get_collect_cap_hours(user_doc)
        elapsed = (now - last_collect).total_seconds()
        capped = elapsed if cap_hours == float("inf") else min(elapsed, cap_hours * 3600)
        multiplier = get_bean_multiplier(user_doc)
        earned = round(rate * (capped / 3600) * multiplier)

        if earned < 1:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="Nothing to collect yet — your generators need a little more time.",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        database.users.update_one(
            {"_id": str(ctx.user.id)},
            {
                "$inc": {"beans": earned, "totalBeansEarned": earned},
                "$set": {"lastCollect": now},
            },
        )
        unlocked = check_achievements(ctx.user.id)

        multiplier_str = f" `×{multiplier:.2f}`" if multiplier > 1.01 else ""
        capped_note = (
            f"\n-# Storage was full! Generators hold up to {cap_hours:g}hrs of beans."
            if cap_hours != float("inf") and elapsed > cap_hours * 3600
            else ""
        )
        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title="🛻 Beans collected!",
            description=(
                f"{beans_emoji} `+{earned:,}` beans{multiplier_str}\n"
                f"Production: **{rate:,}**/hr"
                f"{capped_note}{format_unlocks(unlocked)}"
            ),
        )
        await ctx.response.send_message(embed=embed)

    @app_commands.command(name="fish", description="Go fishing for beans (requires a fishing rod)")
    async def fish(self, ctx: Interaction):
        user_doc = find_user_or_default(ctx.user.id)
        inventory = user_doc.get("inventory", {})
        beans_emoji = core.config.data["emojis"]["beans"]
        fish_emoji = core.config.data["emojis"]["fish"]

        if inventory.get("fishing_rod", 0) < 1:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description="You need a 🎣 **Fishing Rod** first. Grab one in `/shop`!",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        now = datetime.now(timezone.utc)
        cooldown = core.config.data["cooldowns"]["fish"]
        last_fish = parse_ts(user_doc.get("lastFish"))
        if (
            last_fish is not None
            and (now - last_fish).total_seconds() < cooldown
            and not os.getenv("DEV")
        ):
            ready_at = int(last_fish.timestamp()) + cooldown
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description=f"The fish aren't biting yet. Try again <t:{ready_at}:R>.",
            )
            return await ctx.response.send_message(embed=embed, ephemeral=True)

        multiplier = get_bean_multiplier(user_doc)
        earned = round(
            random.randint(
                core.config.data["beans"]["fish"]["min"],
                core.config.data["beans"]["fish"]["max"],
            )
            * multiplier
        )

        database.users.update_one(
            {"_id": str(ctx.user.id)},
            {
                "$inc": {"beans": earned, "totalBeansEarned": earned},
                "$set": {"lastFish": now},
            },
        )
        unlocked = check_achievements(ctx.user.id)

        message = random.choice(core.config.data["messages"]["fishing"])
        multiplier_str = f" `×{multiplier:.2f}`" if multiplier > 1.01 else ""
        embed = Embed(
            color=core.config.data["colors"]["primary"],
            title=f"{fish_emoji} You caught some beans!",
            description=(
                f"{beans_emoji} `+{earned:,}` beans{multiplier_str}\n"
                f"-# {message}{format_unlocks(unlocked)}"
            ),
        )
        await ctx.response.send_message(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Economy(bot))
