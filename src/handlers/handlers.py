from handlers.finder_handler import (
    choose_province,
)
from handlers.listing_handler import (
    case_details_callback,
    listing_command,
    pagination_callback,
)
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
import logging

# Import your text-getting function and other constants
from constants import (
    CASE_DETAILS,
    CASE_LIST,
    CHOOSE_PROVINCE,
    CREATE_CASE_PHOTO,
    CREATE_CASE_REWARD_TYPE,
    CREATE_CASE_SUBMIT,
    ENTER_LOCATION,
    ENTER_PRIVATE_KEY,
    TRANSFER_CONFIRMATION,
    UPLOAD_PROOF,
    get_text,
    SELECT_LANG,
    CHOOSE_COUNTRY,
    SHOW_DISCLAIMER,
    CHOOSE_CITY,
    CHOOSE_ACTION,
    CHOOSE_WALLET_TYPE,
    NAME_WALLET,
    # Conversation state constants for creating a case:
    CREATE_CASE_NAME,
    CREATE_CASE_MOBILE,
    CREATE_CASE_TAC,
    CREATE_CASE_DISCLAIMER,
    CREATE_CASE_REWARD_AMOUNT,
    CREATE_CASE_PERSON_NAME,
    CREATE_CASE_RELATIONSHIP,
    # CREATE_CASE_PHOTO,
    CREATE_CASE_LAST_SEEN_LOCATION,
    CREATE_CASE_SEX,
    CREATE_CASE_AGE,
    CREATE_CASE_HAIR_COLOR,
    CREATE_CASE_EYE_COLOR,
    CREATE_CASE_HEIGHT,
    CREATE_CASE_WEIGHT,
    CREATE_CASE_DISTINCTIVE_FEATURES,
    END,
    WAITING_FOR_MOBILE,
    WALLET_MENU,
    SETTINGS_MENU,
)
from utils.wallet import load_user_wallet
from handlers.start_handler import (
    start,
    select_lang_callback,
    choose_country,
    country_callback,
    disclaimer_callback,
    choose_city,
    city_callback,
    action_callback,
    wallet_type_callback,
    wallet_name_handler,
    cancel,
    error_handler,
)
from handlers.wallet_handler import wallet_command, wallet_menu_callback
from handlers.case_handler import (
    handle_age,
    handle_distinctive_features,
    handle_eye_color,
    handle_hair_color,
    handle_height,
    handle_last_seen_location,
    handle_name,
    handle_mobile,
    handle_person_name,
    handle_photo,
    handle_private_key,
    handle_reason_for_finding,
    handle_relationship,
    handle_reward_type,
    handle_sex,
    handle_tac,
    handle_transfer_confirmation,
    handle_weight,
    disclaimer_2_callback,
    handle_reward_amount,
)
from handlers.settings_handler import (
    settings_command,
    settings_menu_callback,
    mobile_number_handler,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Create Case Handlers (with separate states for each person detail) ---


# --- Conversation Handlers ---

# Main conversation handler for the bot
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        SELECT_LANG: [CallbackQueryHandler(select_lang_callback, pattern="^lang_")],
        CHOOSE_COUNTRY: [
            CallbackQueryHandler(
                country_callback, pattern="^(country_select_|country_page_)"
            ),
            MessageHandler(filters.TEXT & ~filters.COMMAND, choose_country),
        ],
        SHOW_DISCLAIMER: [
            CallbackQueryHandler(disclaimer_callback, pattern="^(agree|disagree)$")
        ],
        CHOOSE_CITY: [
            CallbackQueryHandler(city_callback, pattern="^(city_select_|city_page_)"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, choose_city),
        ],
        CHOOSE_ACTION: [
            CallbackQueryHandler(action_callback, pattern="^(advertise|find_people)$")
        ],
        CHOOSE_WALLET_TYPE: [
            CallbackQueryHandler(wallet_type_callback, pattern="^(SOL|BTC)$")
        ],
        NAME_WALLET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_name_handler)
        ],
        # Create Case Flow:
        CREATE_CASE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)
        ],
        CREATE_CASE_MOBILE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mobile)
        ],
        CREATE_CASE_TAC: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tac)],
        CREATE_CASE_DISCLAIMER: [
            CallbackQueryHandler(disclaimer_2_callback, pattern="^(agree|disagree)$")
        ],
        CREATE_CASE_REWARD_TYPE: [
            CallbackQueryHandler(handle_reward_type, pattern="^(SOL|BTC)$"),
        ],
        CREATE_CASE_REWARD_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reward_amount),
        ],
        CREATE_CASE_PERSON_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_person_name)
        ],
        CREATE_CASE_RELATIONSHIP: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_relationship)
        ],
        CREATE_CASE_PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
        CREATE_CASE_LAST_SEEN_LOCATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_last_seen_location)
        ],
        CREATE_CASE_SEX: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sex)],
        CREATE_CASE_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)],
        CREATE_CASE_HAIR_COLOR: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hair_color)
        ],
        CREATE_CASE_EYE_COLOR: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_eye_color)
        ],
        CREATE_CASE_HEIGHT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_height)
        ],
        CREATE_CASE_WEIGHT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight)
        ],
        CREATE_CASE_DISTINCTIVE_FEATURES: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_distinctive_features)
        ],
        CREATE_CASE_SUBMIT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reason_for_finding)
        ],
        ENTER_PRIVATE_KEY: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_private_key),
        ],
        TRANSFER_CONFIRMATION: [
            CallbackQueryHandler(
                handle_transfer_confirmation, pattern="^(confirm|cancel)$"
            ),
        ],
        # From here the finder is the one who is going to find the person
        CHOOSE_PROVINCE: [CallbackQueryHandler(choose_province, pattern="^province_")],
        # CASE_LIST: [CallbackQueryHandler(show_advertisements, pattern="^page_|^case_")],
        # CASE_DETAILS: [CallbackQueryHandler(case_details_callback, pattern="^case_")],
        # UPLOAD_PROOF: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_proof)],
        # ENTER_LOCATION: [
        #     MessageHandler(filters.TEXT & ~filters.COMMAND, notify_advertiser)
        # ],
        END: [CommandHandler("start", start)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)

# Wallet conversation handler
wallet_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("wallet", wallet_command)],
    states={
        WALLET_MENU: [
            CallbackQueryHandler(
                wallet_menu_callback,
                pattern="^(wallet_refresh|wallet_sol|wallet_btc|wallet_show|wallet_create|wallet_delete)$",
            )
        ],
        NAME_WALLET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_name_handler)
        ],
        END: [CommandHandler("wallet", wallet_command)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)


# Define ConversationHandler
# Define ConversationHandler
case_listing_handler = ConversationHandler(
    entry_points=[CommandHandler("listing", listing_command)],
    states={
        CASE_DETAILS: [
            CallbackQueryHandler(case_details_callback, pattern="^case_.*$"),
            CallbackQueryHandler(
                pagination_callback, pattern="^(page_previous|page_next)$"
            ),
        ]
    },
    fallbacks=[CommandHandler("cancel", lambda update, context: END)],
)

# Settings conversation handler
settings_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("settings", settings_command)],
    states={
        SETTINGS_MENU: [
            CallbackQueryHandler(
                settings_menu_callback,
                pattern="^(settings_language|settings_mobile|settings_close|setlang_)",
            )
        ],
        WAITING_FOR_MOBILE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, mobile_number_handler)
        ],
        END: [CommandHandler("settings", settings_command)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# --- Application Setup ---


def main() -> None:
    # Create the Application and pass it your bot's token.
    application = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    # Add conversation handlers
    application.add_handler(conv_handler)
    application.add_handler(case_listing_handler)
    application.add_handler(wallet_conv_handler)
    application.add_handler(settings_conv_handler)

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
