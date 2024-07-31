from discord import app_commands, Interaction, Embed
from discord.ext.commands import Cog
from src.core import core
from src.bot import Bot


class Ping(Cog):
    """Ping cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Pings the bot!")
    async def ping(self, ctx: Interaction):
        """Pings the bot."""
        ping = round(self.bot.latency * 1000)

        embed = Embed(
            color=core.config.data["colors"]["primary"],
            description=f"{core.config.data['emojis']['ping']} Pong! I took `{ping}ms` to respond.",
        )

        await ctx.response.send_message(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Ping(bot))
