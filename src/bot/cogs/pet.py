import os
import random
from PIL import Image
from io import BytesIO
from traceback import print_exc
from discord import app_commands, Interaction, Embed, File
from discord.ext.commands import Cog
from src.core import core, logger
from src.bot import Bot
from src.utils.images import resize_and_crop

ROOT_DIR = os.path.dirname(os.path.abspath("__main__"))


def get_random_cat():
    taiga_dir = os.path.join(ROOT_DIR, "assets", "taiga")
    taigas = os.listdir(taiga_dir)
    taiga_file = taigas[random.randint(0, len(taiga_dir) - 1)]
    taiga_path = os.path.join(taiga_dir, taiga_file)
    logger.debug(taiga_path)
    return taiga_path


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
            # Get random taiga picture
            taiga_path = get_random_cat()
            taiga_file = File(taiga_path, filename="el_gato.png")

            # * Yes, I used chatgipity for the img manipulation code
            # * But I'm on a time crunch so shhh
            # Load and reformat the image
            image = Image.open(taiga_path)
            processed_image = resize_and_crop(image, (1000, 1000))
            rotated_image = processed_image.rotate(0)

            # Save the processed image to a buffer
            buffer = BytesIO()
            rotated_image.save(buffer, format="PNG")
            buffer.seek(0)

            # Create a discord file from the buffer
            taiga_file = File(fp=buffer, filename="el_gato.png")

            # Create embed
            embed = Embed(
                title=f"You have pet {core.config.data['bot']['name']}",
                color=core.config.data["colors"]["primary"],
                description=f"""
{core.config.data['bot']['name']} has given you some beans!
{core.config.data['emojis']['beans']} `+{{beans_added}}`
**Stats**
{core.config.data['emojis']['heart']} Pets `{{pets}}`
{core.config.data['emojis']['beans']} Beans `{{total_beans}}`
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
