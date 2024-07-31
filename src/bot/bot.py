import os
from cogwatch import watch
from discord import Intents, CustomActivity
from discord.ext.commands import AutoShardedBot
from src.utils import logger
from src.core import core


class Bot(AutoShardedBot):
    """The main bot class, using autosharding."""

    def __init__(self, **options) -> None:
        super().__init__(
            command_prefix=core.config.data["bot"]["prefix"],
            intents=Intents.default(),
            **options,
        )

    async def start(self):
        """Starts the bot using the token in the env."""
        try:
            logger.info("Starting the bot")
            await super().start(os.getenv("BOT_TOKEN"), reconnect=True)
        except Exception as e:
            raise Exception(f"Bot failed to startup: {e}")

    async def load_extensions(self):
        """Loads all the extensions / cogs in the ./cogs folder"""
        for f in os.listdir("./src/bot/cogs"):
            if f.endswith(".py"):
                await self.load_extension("src.bot.cogs." + f[:-3])
                logger.info(f"Successfully loaded cog: {f[:-3]}")

    async def setup_hook(self):
        """Called on setup, loads extensions"""
        await self.load_extensions()
        await self.tree.sync()

    @watch(path="src/bot/cogs", colors=True)
    async def on_ready(self):
        """On ready event, sets presence"""
        try:
            activity: str = core.config.data["bot"]["activity"]
            logger.debug(f"Activity: {activity}")
            custom_activity = CustomActivity(activity)
            await self.change_presence(
                status=core.config.data["bot"]["status"], activity=custom_activity
            )
            logger.info("Set status completed")
        except Exception as e:
            logger.error(f"Error setting presence: {e}")

        logger.info("Bot is ready")
