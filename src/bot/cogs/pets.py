import os
import random
from PIL import Image
from io import BytesIO
from traceback import print_exc
from datetime import datetime, timezone, timedelta
from discord import app_commands, Interaction, Embed, File
from discord.ext.commands import Cog
from src.database.database import database
from src.core import core, logger
from src.bot import Bot
from src.utils.images import resize_and_crop
from src.utils.user import find_user_or_default
from src.bot.cogs.shop import get_cooldown_reduction, MIN_COOLDOWN

ROOT_DIR = os.path.dirname(os.path.abspath("__main__"))


def get_random_cat():
    taiga_dir = os.path.join(ROOT_DIR, "assets", "taiga")
    taigas = os.listdir(taiga_dir)
    taiga_file = random.choice(taigas)
    taiga_path = os.path.join(taiga_dir, taiga_file)
    logger.debug(taiga_path)
    return taiga_path


def calculate_beans(
    initial: int = 0,
    min: int = core.config.data["beans"]["pets"]["min"],
    max: int = core.config.data["beans"]["pets"]["max"],
):
    """Calculates a new random number of beans and adds it to the initial.

    Args:
        initial (int, optional): The initial value of beans. Defaults to 0.
        min (int, optional): The min number of beans given. Defaults to core.config.data["beans"]["pets"]["min"].
        max (int, optional): The max number of beans given. Defaults to core.config.data["beans"]["pets"]["max"].

    Returns:
        _type_: _description_
    """
    new_beans = random.randint(min, max)
    new_total = initial + new_beans
    return new_beans, new_total


class Pet(Cog):
    """Pet cog"""

    def __init__(self, bot: Bot):
        self.bot = bot

    @app_commands.command(
        name="pet", description=f"Pet {core.config.data['bot']['name']}!"
    )
    async def pet(self, ctx: Interaction):
        """Pets the bot."""
        try:
            # Get user doc
            user_doc: dict = find_user_or_default(ctx.user.id)
            last_pet = user_doc["lastPet"]
            continue_streak = False

            if last_pet is not None:
                # Parse last pet timestamp
                date_format = "%Y-%m-%d %H:%M:%S.%f %z"
                time_last_pet: datetime = (
                    datetime.strptime(last_pet, date_format)
                    if isinstance(last_pet, str)
                    else last_pet
                )
                if time_last_pet.tzinfo is None:
                    time_last_pet = time_last_pet.replace(tzinfo=timezone.utc)

                time_now = datetime.now(timezone.utc)
                last_pet_dif = time_now - time_last_pet

                inventory = user_doc.get("inventory", {})
                base_cooldown = core.config.data["cooldowns"]["pet"]
                pet_cooldown = max(base_cooldown - get_cooldown_reduction(inventory), MIN_COOLDOWN)

                if not os.getenv("DEV"):
                    if last_pet_dif.total_seconds() < pet_cooldown:
                        cooldown_over = time_last_pet + timedelta(seconds=pet_cooldown)
                        cooldown_over_ts = f"<t:{int(cooldown_over.timestamp())}:R>"

                        embed = Embed(
                            color=core.config.data["colors"]["error"],
                            description=f"{core.config.data['bot']['name']} is sleeping right now. Come back {cooldown_over_ts}.",
                        )
                        return await ctx.response.send_message(embed=embed)

                if last_pet_dif.total_seconds() < 86400 or os.getenv("DEV"):
                    continue_streak = True

            # Get random number of beans
            new_beans, new_beans_total = calculate_beans(initial=user_doc["beans"])

            # Update database
            new_pets = user_doc["pets"] + 1
            new_streak = user_doc.get("streak", 0) + 1 if continue_streak else 0
            database.users.find_one_and_update(
                {"_id": str(ctx.user.id)},
                {"$set": {
                    "beans": new_beans_total,
                    "pets": new_pets,
                    "lastPet": datetime.now(timezone.utc),
                    "streak": new_streak,
                    "highestStreak": max(new_streak, user_doc.get("highestStreak", 0)),
                    "alarmSent": False,
                }},
            )

            # Load, crop, and buffer the image
            taiga_path = get_random_cat()
            image = Image.open(taiga_path)
            processed_image = resize_and_crop(image, (1000, 1000))
            buffer = BytesIO()
            processed_image.save(buffer, format="PNG")
            buffer.seek(0)
            taiga_file = File(fp=buffer, filename="el_gato.png")

            streak_line = f"\nStreak: **{new_streak}**!" if new_streak >= 2 else ""
            embed = Embed(
                title=f"You pet {core.config.data['bot']['name']}!",
                color=core.config.data["colors"]["primary"],
                description=(
                    "Taiga has given you some beans!\n"
                    f"{core.config.data['emojis']['beans']} `+{new_beans}` beans\n\n"
                    f"**Stats**\n"
                    f"{core.config.data['emojis']['heart']} Pets `{new_pets}`\n"
                    f"{core.config.data['emojis']['beans']} Beans `{new_beans_total}`"
                    + streak_line
                ),
            )
            embed.set_image(url="attachment://el_gato.png")

            await ctx.response.send_message(file=taiga_file, embed=embed)
        except Exception as e:
            print_exc()
            logger.error("An error has occured:", e)
            raise e


async def setup(bot: Bot):
    await bot.add_cog(Pet(bot))
