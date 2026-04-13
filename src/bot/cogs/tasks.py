from datetime import datetime, timezone, timedelta
from discord import Embed
from discord.ext import tasks
from discord.ext.commands import Cog
import discord

from src.bot import Bot
from src.core import core, logger
from src.database.database import database
from src.bot.cogs.shop import get_cooldown_reduction, MIN_COOLDOWN


class Tasks(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.alarm_clock_check.start()

    def cog_unload(self):
        self.alarm_clock_check.cancel()

    @tasks.loop(seconds=60)
    async def alarm_clock_check(self):
        now = datetime.now(timezone.utc)
        try:
            cursor = database.users.find({
                "inventory.alarm_clock": {"$gte": 1},
                "lastPet": {"$ne": None, "$lte": now - timedelta(seconds=MIN_COOLDOWN)},
                "alarmSent": {"$ne": True},
            })
            for user_doc in cursor:
                inventory = user_doc.get("inventory", {})
                base_cooldown = core.config.data["cooldowns"]["pet"]
                effective_cooldown = max(
                    base_cooldown - get_cooldown_reduction(inventory), MIN_COOLDOWN
                )

                last_pet = user_doc["lastPet"]
                if isinstance(last_pet, str):
                    last_pet = datetime.strptime(last_pet, "%Y-%m-%d %H:%M:%S.%f %z")
                if last_pet.tzinfo is None:
                    last_pet = last_pet.replace(tzinfo=timezone.utc)

                if (now - last_pet).total_seconds() < effective_cooldown:
                    continue

                # Mark sent BEFORE DM attempt
                database.users.update_one(
                    {"_id": user_doc["_id"]},
                    {"$set": {"alarmSent": True}},
                )

                try:
                    discord_user = await self.bot.fetch_user(int(user_doc["_id"]))
                    embed = Embed(
                        color=core.config.data["colors"]["primary"],
                        title=f"⏰ {core.config.data['bot']['name']} is ready to be pet!",
                        description="Your cooldown has expired. Head back and use `/pet`!",
                    )
                    await discord_user.send(embed=embed)
                    logger.debug(f"Alarm sent to {user_doc['_id']}")
                except discord.Forbidden:
                    logger.debug(f"Could not DM {user_doc['_id']} (DMs closed)")
                except discord.NotFound:
                    logger.debug(f"User {user_doc['_id']} not found")
                except Exception as e:
                    logger.error(f"Alarm DM error for {user_doc['_id']}: {e}")

        except Exception as e:
            logger.error(f"alarm_clock_check error: {e}")

    @alarm_clock_check.before_loop
    async def before_alarm_clock_check(self):
        await self.bot.wait_until_ready()


async def setup(bot: Bot):
    await bot.add_cog(Tasks(bot))
