import asyncio
from src.bot import Bot
from src.utils import logger

bot = Bot()


async def start():
    logger.info("Starting Process")
    try:
        await bot.start()
    except asyncio.CancelledError:
        logger.warning("Asyncio CancelledError: stopping process...")
        await bot.close()


try:
    asyncio.run(start())
except KeyboardInterrupt:
    pass
