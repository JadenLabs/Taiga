from datetime import datetime, timezone, timedelta
from discord import app_commands, Interaction, Embed, User
from discord.ext.commands import Cog
from src.core import core
from src.bot import Bot
from src.database.database import database


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

        user = user if user else ctx.user
        user_doc = database.users.find_one({"_id": str(user.id)})
        if user_doc is None:
            embed = Embed(
                color=core.config.data["colors"]["error"],
                description=f"{core.config.data['emojis']['false']} This user has not used taiga",
            )

            return await ctx.edit_original_response(embed=embed)

        # Calculate cooldowns
        last_pet = user_doc.get("lastPet")
        if last_pet is not None:
            date_format = "%Y-%m-%d %H:%M:%S.%f %z"
            time_last_pet: datetime = (
                datetime.strptime(last_pet, date_format)
                if isinstance(last_pet, str)
                else last_pet
            )
            if time_last_pet.tzinfo is None:
                time_last_pet = time_last_pet.replace(tzinfo=timezone.utc)

            pet_cooldown = core.config.data["cooldowns"]["pet"]
            cooldown_over = time_last_pet + timedelta(seconds=pet_cooldown)
            cooldown_over_ts = f"<t:{int(cooldown_over.timestamp())}:R>"
        else:
            cooldown_over_ts = "`has not pet`"

        embed = Embed(
            color=core.config.data["colors"]["invisible"],
            title=f"{user.name}'s Profile",
            description=f"""\
""",
        )
        embed.add_field(
            name="Stats",
            value=f"""\
{core.config.data['emojis']['heart']} Pets: `{user_doc.get("pets", 0)}`
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

        await ctx.edit_original_response(embed=embed)


async def setup(bot: Bot):
    await bot.add_cog(Profile(bot))
