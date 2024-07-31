from discord import Embed
from src.core import core


async def basic_error_embed(message: str, **embed_options):
    """Create a basic error embed

    Args:
        message (str): The message to display in the embed

    Returns:
        Embed: The error embed
    """
    description = f"{core.config.data['emojis']['false']} {message}"
    return Embed(
        description=description,
        color=core.config.data["colors"]["error"],
        **embed_options,
    )
