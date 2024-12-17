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

ROOT_DIR = os.path.dirname(os.path.abspath("__main__"))


def get_random_cat():
    taiga_dir = os.path.join(ROOT_DIR, "assets", "taiga")
    taigas = os.listdir(taiga_dir)
    taiga_file = taigas[random.randint(0, len(taiga_dir) - 1)]
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

            # Check last pet

            if last_pet is not None:
                # Format the last pet into a datetime
                date_format = "%Y-%m-%d %H:%M:%S.%f %z"
                time_last_pet: datetime = (
                    datetime.strptime(last_pet, date_format)
                    if isinstance(last_pet, str)
                    else last_pet
                )
                if time_last_pet.tzinfo is None:
                    time_last_pet = time_last_pet.replace(tzinfo=timezone.utc)

                # Calculate time since last pet in regards to cooldown
                time_now = datetime.now(timezone.utc)
                last_pet_dif = time_now - time_last_pet
                pet_cooldown = core.config.data["cooldowns"]["pet"]

                # if (
                #     ctx.user.id not in core.config.data["ids"]["sudo_users"]
                # ):  # ! COMMENT OUT WHEN NOT IN DEV MODE
                if last_pet_dif.total_seconds() < pet_cooldown:
                    cooldown_over = time_last_pet + timedelta(seconds=pet_cooldown)
                    cooldown_over_ts = f"<t:{int(cooldown_over.timestamp())}:R>"

                    embed = Embed(
                        color=core.config.data["colors"]["error"],
                        title="Sorry,",
                        description=f"{core.config.data['bot']['name']} is sleeping right now, please come back {cooldown_over_ts}.",
                    )

                    return await ctx.response.send_message(embed=embed)

                # Check if user has pet in the last 24 hrs
                if last_pet_dif.total_seconds() < 86400:
                    continue_streak = True

            # Get random number of beans
            new_beans, new_beans_total = calculate_beans(initial=user_doc["beans"])

            # Update database
            new_pets = user_doc["pets"] + 1
            time_now = datetime.now(timezone.utc)
            new_streak = user_doc.get("streak", 0) + 1 if continue_streak else 0
            set_query = {
                "beans": new_beans_total,
                "pets": new_pets,
                "lastPet": time_now,
                "streak": new_streak,
            }

            # Update doc
            database.users.find_one_and_update(
                {"_id": str(ctx.user.id)},
                {"$set": set_query},
            )

            # Get random taiga picture
            taiga_path = get_random_cat()
            taiga_file = File(taiga_path, filename="el_gato.png")

            # Load and reformat the image
            image = Image.open(taiga_path)
            processed_image = resize_and_crop(image, (1000, 1000))
            rotated_image = processed_image.rotate(0)

            # Save the image to a buffer
            buffer = BytesIO()
            rotated_image.save(buffer, format="PNG")
            buffer.seek(0)

            # Create a file from the buffer
            taiga_file = File(fp=buffer, filename="el_gato.png")

            # Show streak if the streak is greater than or equal to 2
            fmt_streak = (
                f"\nYou have a streak of **{new_streak}**!" if new_streak >= 2 else ""
            )

            # Create embed
            embed = Embed(
                title=f"You have pet {core.config.data['bot']['name']}",
                color=core.config.data["colors"]["primary"],
                description=f"""
{core.config.data['bot']['name']} has given you some beans!
{core.config.data['emojis']['beans']} `+{new_beans}`
**Stats**
{core.config.data['emojis']['heart']} Pets `{new_pets}`
{core.config.data['emojis']['beans']} Beans `{new_beans_total}`
{fmt_streak}
""",
            )
            embed.set_image(url=f"attachment://el_gato.png")

            # Respond
            await ctx.response.send_message(file=taiga_file, embed=embed)
        except Exception as e:
            print_exc()
            logger.error("An error has occured:", e)
            raise e


async def setup(bot: Bot):
    await bot.add_cog(Pet(bot))
