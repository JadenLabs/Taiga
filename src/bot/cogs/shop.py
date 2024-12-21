from discord import app_commands, Interaction, Embed
from discord.ext.commands import Cog
from src.core import core
from src.bot import Bot


class Shop(Cog):
    """Shop cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="shop", description="Open the shop")
    async def shop(self, ctx: Interaction):
        """Open the shop"""
        embed = Embed(
            color=core.config.data["colors"]["primary"],
            description=f"work in progress",
        )

        await ctx.response.send_message(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Shop(bot))
