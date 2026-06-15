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
from src.bot.cogs.shop import (
    get_bean_multiplier,
    get_effective_cooldown,
    get_golden_pet_chance,
    check_achievements,
    format_unlocks,
)

GOLDEN_PET_CHANCE = 0.05
GOLDEN_PET_MULTIPLIER = 10

ROOT_DIR = os.path.dirname(os.path.abspath("__main__"))


def get_random_cat():
    taiga_dir = os.path.join(ROOT_DIR, "assets", "taiga")
    taigas = os.listdir(taiga_dir)
    taiga_file = random.choice(taigas)
    taiga_path = os.path.join(taiga_dir, taiga_file)
    logger.debug(taiga_path)
    return taiga_path


def streak_multiplier(streak: int) -> float:
    """Quadratic streak multiplier capped at 40×.
    M(n) = 1 + n*(n-1)/76 - designed so 20 consecutive pets total ~50,000 beans."""
    return min(1.0 + (streak * (streak - 1)) / 76.0, 40.0)


def calculate_beans(
    initial: int = 0,
    min: int = core.config.data["beans"]["pets"]["min"],
    max: int = core.config.data["beans"]["pets"]["max"],
    multiplier: float = 1.0,
):
    new_beans = round(random.randint(min, max) * multiplier)
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
            inventory = user_doc.get("inventory", {})
            continue_streak = False
            used_streak_freeze = False

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

                pet_cooldown = get_effective_cooldown(user_doc)

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
                elif (
                    user_doc.get("streak", 0) > 0
                    and inventory.get("streak_freeze", 0) >= 1
                ):
                    # A streak freeze saves the streak from a missed day
                    continue_streak = True
                    used_streak_freeze = True

            # Calculate streak before beans so multiplier can use it
            new_pets = user_doc["pets"] + 1
            new_streak = user_doc.get("streak", 0) + 1 if continue_streak else 0

            # Golden pet roll: lucky collar grants the base chance, Lucky
            # Whiskers (permanent upgrade) adds on top and works on its own.
            golden_chance = get_golden_pet_chance(user_doc)
            if inventory.get("lucky_collar", 0) >= 1:
                golden_chance += GOLDEN_PET_CHANCE
            golden_pet = golden_chance > 0 and random.random() < golden_chance

            multiplier = streak_multiplier(new_streak) * get_bean_multiplier(user_doc)
            if golden_pet:
                multiplier *= GOLDEN_PET_MULTIPLIER
            new_beans, new_beans_total = calculate_beans(
                initial=user_doc["beans"], multiplier=multiplier
            )

            # Update database
            update = {
                "$set": {
                    "beans": new_beans_total,
                    "pets": new_pets,
                    "lastPet": datetime.now(timezone.utc),
                    "streak": new_streak,
                    "highestStreak": max(new_streak, user_doc.get("highestStreak", 0)),
                    "alarmSent": False,
                    "streakAlarmSent": False,
                },
            }
            inc = {"totalBeansEarned": new_beans}
            if used_streak_freeze:
                inc["inventory.streak_freeze"] = -1
            update["$inc"] = inc
            database.users.find_one_and_update({"_id": str(ctx.user.id)}, update)

            # Unlock any achievements crossed by this pet (pets/streak/lifetime)
            unlocked = check_achievements(ctx.user.id)

            # Load, crop, and buffer the image
            taiga_path = get_random_cat()
            image = Image.open(taiga_path)
            processed_image = resize_and_crop(image, (1000, 1000))
            buffer = BytesIO()
            processed_image.save(buffer, format="PNG")
            buffer.seek(0)
            taiga_file = File(fp=buffer, filename="el_gato.png")

            multiplier_str = f" `×{multiplier:.2f}`" if multiplier > 1.01 else ""
            streak_line = (
                f"\nStreak: **{new_streak}**{multiplier_str}!"
                if new_streak >= 2
                else ""
            )
            golden_line = (
                f"\n{core.config.data['emojis']['golden_beans']} **GOLDEN PET!** ×{GOLDEN_PET_MULTIPLIER} beans!"
                if golden_pet
                else ""
            )
            freeze_line = (
                f"\n🧊 A streak freeze saved your streak! ({inventory.get('streak_freeze', 0) - 1} left)"
                if used_streak_freeze
                else ""
            )
            title = (
                f"✨ You pet {core.config.data['bot']['name']}! ✨"
                if golden_pet
                else f"You pet {core.config.data['bot']['name']}!"
            )
            embed = Embed(
                title=title,
                color=(
                    core.config.data["colors"]["secondary"]
                    if golden_pet
                    else core.config.data["colors"]["primary"]
                ),
                description=(
                    "Taiga has given you some beans!\n"
                    f"{core.config.data['emojis']['beans']} `+{new_beans}` beans"
                    f"{golden_line}{freeze_line}\n\n"
                    f"**Stats**\n"
                    f"{core.config.data['emojis']['heart']} Pets `{new_pets}`\n"
                    f"{core.config.data['emojis']['beans']} Beans `{new_beans_total}`"
                    + streak_line
                    + format_unlocks(unlocked)
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
