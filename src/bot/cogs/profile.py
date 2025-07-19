from discord import app_commands, Interaction, Embed, User
from discord.ext.commands import Cog
from src.core import core
from src.bot import Bot
from src.database.database import database
from src.utils.user import (
    get_time_last_pet,
    get_pet_cooldown_over,
    get_pet_cooldown_over_ts,
)


class Profile(Cog):
    """Profile cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="View the profile of a user")
    async def profile(self, ctx: Interaction, user: User = None):
        """View the profile of a user

        Args:
            ctx (Interaction): The command interaction.
            user (User, optional): The user to get the profile of.
        """
        await ctx.response.defer()

        user = user or ctx.user
        user_doc = database.users.find_one({"_id": str(user.id)})
        if user_doc is None:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description=f"{core.config.data['emojis']['false']} This user has not used taiga.",
            )

            return await ctx.edit_original_response(embed=embed)

        # Calculate cooldowns
        time_last_pet = get_time_last_pet(user_doc)
        if time_last_pet:
            cooldown_over = get_pet_cooldown_over(time_last_pet)
            cooldown_over_ts = get_pet_cooldown_over_ts(cooldown_over)
        else:
            cooldown_over_ts = "`has not pet`"

        # Create embed
        embed = Embed(
            color=core.config.data["colors"]["invisible"],
            title=f"{user.name}'s Profile",
            description=f"""\
""",
        )
        embed.add_field(
            name="Stats",
            value=f"""\
{core.config.data['emojis']['heart']} Pets: `{user_doc.get("pets", 0)}` (streak: `{user_doc.get("streak", 0)}`)
{core.config.data['emojis']['beans']} Beans: `{user_doc.get("beans", 0)}`
""",
        )
        embed.add_field(
            name="Cooldowns",
            value=f"""\
- Pet: {cooldown_over_ts}
""",
            inline=True,
        )
        if user.avatar.url:
            embed.set_thumbnail(url=user.avatar.url)

        # Send response
        await ctx.edit_original_response(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Profile(bot))
