import sys
import os
import logging
import asyncio
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from models.case_model import Case
from telegram.ext import ApplicationBuilder
from handlers.handlers import (
    conv_handler,
    wallet_conv_handler,
    settings_conv_handler,
    case_listing_handler,
)
from handlers.start_handler import error_handler, setup_logging
from config.config_manager import MONGODB_NAME, MONGODB_URI
from src.config.config_manager import TOKEN


sys.path.append(os.path.join(os.path.dirname(__file__), "src"))


setup_logging()


async def main_setup():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(conv_handler)
    application.add_handler(wallet_conv_handler)
    application.add_handler(settings_conv_handler)
    application.add_handler(case_listing_handler)

    application.add_error_handler(error_handler)

    logger = logging.getLogger(__name__)
    logger.info("Bot is starting...")
    await application.run_polling()


async def init_db():
    try:
        client = AsyncIOMotorClient(MONGODB_URI)
        await init_beanie(database=client[MONGODB_NAME], document_models=[Case])
        print("Database Connected Successfully 🚀.")
        await main_setup()
    except Exception as e:
        print(f"\033[91mError initializing database: {e}\033[0m")


async def main():
    await init_db()


if __name__ == "__main__":
    import nest_asyncio

    nest_asyncio.apply()

    try:
        loop = asyncio.get_running_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())
