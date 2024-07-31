from discord import Guild
from discord.ext.commands import Cog
from src.bot.bot import Bot
from src.utils import logger


class Client(Cog):
    """Client Events"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_connect(self):
        logger.info("Client has connected")

    @Cog.listener()
    async def on_disconnect(self):
        logger.warn("Client has disconnected")

    @Cog.listener()
    async def on_shard_connect(self, shard_id: int):
        logger.info(f"Shard #{shard_id} has connected")

    @Cog.listener()
    async def on_shard_disconnect(self, shard_id: int):
        logger.warn(f"Shard #{shard_id} has disconnected")

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        logger.info(f"Client has joined {guild.id}")

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        logger.info(f"Client has left {guild.id}")

    @Cog.listener()
    async def on_shard_ready(self, shard_id: int):
        logger.info(f"Shard {shard_id} ready")


async def setup(bot: Bot):
    await bot.add_cog(Client(bot))
