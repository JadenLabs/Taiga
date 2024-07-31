from discord import Interaction, AppCommandType
from discord.ext.commands import Cog, CheckFailure, Context, CommandError
from src.bot.bot import Bot
from src.core import core
from src.utils import logger
from src.messages.errors import basic_error_embed

import traceback
import sys


class Cmds(Cog):
    """Commands Events"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        # ! BUG: Doesn't seem to trigger when there is an error.

        if isinstance(error, CheckFailure):
            await ctx.send(
                embed=basic_error_embed(
                    "You do not have the permissions to run this command."
                )
            )
        else:
            await ctx.send(embed=basic_error_embed("An unknown error has occured."))
            logger.error(f"App command error: %s", error, exc_info=1)
            traceback.print_exception(
                type(error), error, error.__traceback__, file=sys.stderr
            )

    @Cog.listener()
    async def on_app_command_completion(
        self, ctx: Interaction, command: AppCommandType
    ):
        from_message = f"${ctx.guild.id}" if ctx.guild else "in DM"
        logger.info(f"{command.name} done {from_message} @{ctx.user.id}")


async def setup(bot: Bot):
    await bot.add_cog(Cmds(bot))
