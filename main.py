import logging
import asyncio
from beanie import init_beanie
from src.models.case_model import Case
from telegram.ext import ApplicationBuilder
from handlers import (
    conv_handler,
    wallet_conv_handler,
    settings_conv_handler,
    case_listing_handler,
)
from utils import error_handler, setup_logging
from motor.motor_asyncio import AsyncIOMotorClient

setup_logging()


async def main_setup():
    TOKEN = "8012413981:AAG-nklE6dsD_RU4bicbF0jJ-Zjrmbab3oM"
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
        client = AsyncIOMotorClient("mongodb://localhost:27017/myproject")
        await init_beanie(database=client["myproject"], document_models=[Case])
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
