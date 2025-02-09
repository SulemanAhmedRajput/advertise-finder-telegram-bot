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

# Setup logging
setup_logging()


# Main setup function for the bot
async def main_setup():
    TOKEN = "8012413981:AAG-nklE6dsD_RU4bicbF0jJ-Zjrmbab3oM"
    application = ApplicationBuilder().token(TOKEN).build()

    # Add conversation handlers
    application.add_handler(conv_handler)
    application.add_handler(wallet_conv_handler)
    application.add_handler(settings_conv_handler)
    application.add_handler(case_listing_handler)

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger = logging.getLogger(__name__)
    logger.info("Bot is starting...")
    await application.run_polling()


# MongoDB initialization
async def init_db():
    try:
        client = AsyncIOMotorClient("mongodb://localhost:27017/myproject")
        await init_beanie(database=client["myproject"], document_models=[Case])
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")


# Main function (entry point)
async def main():
    # Initialize MongoDB and then start the bot
    await init_db()
    await main_setup()


# Running the event loop correctly
if __name__ == "__main__":
    import nest_asyncio

    nest_asyncio.apply()

    try:
        loop = asyncio.get_running_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        asyncio.run(main())
