import logging
from telegram.ext import ApplicationBuilder
from handlers import conv_handler, wallet_conv_handler, settings_conv_handler
from utils import error_handler, setup_logging
from src.utils.db_utils import get_mongo_client, get_database, get_collection

# Setup logging
setup_logging()


# Main function to start the bot
def main():
    TOKEN = "7333467475:AAE-S2Hom4XZI_sfyCbrFrLkmXy6aQpL_GI"
    application = ApplicationBuilder().token(TOKEN).build()

    # MongoDB setup
    mongo_client = get_mongo_client()
    db = get_database(mongo_client)
    users_collection = get_collection(db, "users")

    # Pass the MongoDB collection to handlers if needed
    application.bot_data["users_collection"] = users_collection

    print("MongoDB connection established.")

    # Add conversation handlers
    application.add_handler(conv_handler)
    application.add_handler(wallet_conv_handler)
    application.add_handler(settings_conv_handler)

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger = logging.getLogger(__name__)
    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
