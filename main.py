import logging
import asyncio
import signal
from telegram.ext import ApplicationBuilder
from src.database.mongo import initiate_database
from handlers import conv_handler, wallet_conv_handler, settings_conv_handler
from utils import error_handler, setup_logging
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

# Setup logging
setup_logging()


# Main function to start the bot
async def main():
    TOKEN = "7333467475:AAE-S2Hom4XZI_sfyCbrFrLkmXy6aQpL_GI"
    application = ApplicationBuilder().token(TOKEN).build()

    await initiate_database()

    # Add conversation handlers
    application.add_handler(conv_handler)
    application.add_handler(wallet_conv_handler)
    application.add_handler(settings_conv_handler)

    # Add error handler
    application.add_error_handler(error_handler)

    # Initialize and run the application
    await application.initialize()
    await application.start()
    logger = logging.getLogger(__name__)
    logger.info("Bot is starting...")

    # Run the bot until a termination signal is received
    stop_event = asyncio.Event()
    loop = asyncio.get_event_loop()

    # Signal handler for graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received termination signal. Shutting down...")
        stop_event.set()

    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler, sig, None)

    # Wait for the stop event
    await stop_event.wait()

    # Shut down the application
    logger.info("Bot is shutting down...")
    await application.stop()
    await application.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
