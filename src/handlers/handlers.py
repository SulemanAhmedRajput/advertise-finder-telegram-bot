from handlers.case_handler import disclaimer_2_callback, handle_age, handle_distinctive_features, handle_eye_color, handle_hair_color, handle_height, handle_last_seen_location, handle_mobile, handle_name, handle_person_name, handle_photo, handle_private_key, handle_reason_for_finding, handle_relationship, handle_reward_amount, handle_reward_type, handle_sex, handle_tac, handle_transfer_confirmation, handle_weight
from handlers.finder_handler import (
    show_advertisements,
    case_details,
    handle_proof,
    notify_advertiser,
    handle_found_case,
    province_callback,
    choose_province,
    handle_advertiser_confirmation,
    handle_public_key,
    handle_transfer,
)
from handlers.wallet_handler import cancel_delete_wallet_handler, confirm_delete_wallet_handler, create_wallet_handler,  create_wallet_type_handler, delete_wallet_cancel_handler, delete_wallet_confirm_handler, delete_wallet_handler, refresh_wallets_handler, select_wallet_type_handler, show_address_handler, show_wallets_handler, view_transaction_history_handler, wallet_command
from telegram.ext import (
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
    CREATE_WALLET,
    ENTER_LOCATION,
    ENTER_PRIVATE_KEY,
    HISTORY_MENU,
    MOBILE_MANAGEMENT,
    MOBILE_VERIFICATION,
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
    CASE_DETAILS,
    CASE_LIST,
    ENTER_LOCATION,
    UPLOAD_PROOF,
    ADVERTISER_CONFIRMATION,
    CONFIRM_TRANSFER,
    ENTER_PUBLIC_KEY,
)
from handlers.settings_handler import  handle_setting_mobile, handle_setting_tac, settings_command, settings_menu_callback
from utils.wallet import load_user_wallet
from handlers.start_handler import (
    action_callback,
    choose_city,
    city_callback,
    start,
    select_lang_callback,
    choose_country,
    country_callback,
    disclaimer_callback,
    # choose_city,
    # city_callback,
    # action_callback,
    # wallet_type_callback,
    # wallet_name_handler,
    cancel,
    error_handler,
    wallet_name_handler,
    wallet_selection_callback,
    wallet_type_callback,
)
# from handlers.wallet_handler import wallet_command, wallet_menu_callback
# from handlers.case_handler import (
#     handle_age,
#     handle_distinctive_features,
#     handle_eye_color,
#     handle_hair_color,
#     handle_height,
#     handle_last_seen_location,
#     handle_name,
#     handle_mobile,
#     handle_person_name,
#     handle_photo,
#     handle_private_key,
#     handle_reason_for_finding,
#     handle_relationship,
#     handle_reward_type,
#     handle_sex,
#     handle_tac,
#     handle_transfer_confirmation,
#     handle_weight,
#     disclaimer_2_callback,
#     handle_reward_amount,
# )

# from handlers.settings_handler import (
#     settings_command,
#     settings_menu_callback,
#     mobile_number_handler,
# )


# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Main conversation handler for the bot
start_handler = ConversationHandler(
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
    CallbackQueryHandler(wallet_type_callback, pattern="^(SOL|USDT)$"),
    CallbackQueryHandler(wallet_selection_callback, pattern="^wallet_"),
],
NAME_WALLET: [
    MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_name_handler),
],
        
#         # Create Case Flow:
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
            CallbackQueryHandler(handle_reward_type, pattern="^(SOL|USDT)$"),
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
        CREATE_CASE_SEX: [CallbackQueryHandler(handle_sex)],
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
        CHOOSE_PROVINCE: [
            CallbackQueryHandler(
                province_callback, pattern="^(province_select_|province_page_)"
            ),
            MessageHandler(filters.TEXT & ~filters.COMMAND, choose_province),
        ],
        CASE_LIST: [
            CallbackQueryHandler(show_advertisements, pattern=r"^page_(previous|next)"),
            CallbackQueryHandler(case_details, pattern=r"^case_"),
            CallbackQueryHandler(show_advertisements, pattern="^back_to_list"),
        ],
        CASE_DETAILS: [
            CallbackQueryHandler(case_details, pattern="^case_"),
            CallbackQueryHandler(handle_found_case, pattern="^found_"),  # Add this line
            CallbackQueryHandler(show_advertisements, pattern="^back_to_list"),
        ],
        UPLOAD_PROOF: [MessageHandler(filters.PHOTO | filters.VIDEO, handle_proof)],
        ENTER_LOCATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, notify_advertiser)
        ],
        ADVERTISER_CONFIRMATION: [  # NEW: Advertiser confirms reward
            CallbackQueryHandler(
                handle_advertiser_confirmation,
                pattern="^(approve_reward|reject_reward)$",
            )
        ],
        ENTER_PUBLIC_KEY: [  # NEW: Finder enters their Solana public key
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_public_key)
        ],
        CONFIRM_TRANSFER: [  # NEW: Advertiser confirms SOL transfer
            CallbackQueryHandler(
                handle_transfer, pattern="^(confirm_transfer|cancel_transfer)$"
            )
        ],
        END: [CommandHandler("start", start)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)

# Wallet conversation handler

# Define conversation handler
wallet_handler = ConversationHandler(
    entry_points=[CommandHandler("wallet", wallet_command)],
    states={
        WALLET_MENU: [
            CallbackQueryHandler(select_wallet_type_handler, pattern="^create_wallet$"),
            CallbackQueryHandler(refresh_wallets_handler, pattern="^refresh_wallets$"),
            CallbackQueryHandler(lambda u, c: show_wallets_handler(u, c, "SOL"), pattern="^sol_wallets$"),
            CallbackQueryHandler(lambda u, c: show_wallets_handler(u, c, "USDT"), pattern="^usdt_wallets$"),
            CallbackQueryHandler(show_address_handler, pattern="^show_address_.*$"),
            CallbackQueryHandler(delete_wallet_handler, pattern="^delete_wallet$"),
            CallbackQueryHandler(confirm_delete_wallet_handler, pattern="^confirm_delete_.*$"),
            CallbackQueryHandler(delete_wallet_confirm_handler, pattern="^delete_wallet_confirm$"),
            CallbackQueryHandler(delete_wallet_cancel_handler, pattern="^delete_wallet_cancel$"),
            CallbackQueryHandler(wallet_command, pattern="^back_to_menu$"),
            CallbackQueryHandler(view_transaction_history_handler, pattern="^view_history$"),
        ],
        CREATE_WALLET: [
            CallbackQueryHandler(create_wallet_type_handler, pattern="^sol_wallet_type$"),
            CallbackQueryHandler(create_wallet_type_handler, pattern="^usdt_wallet_type$"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, create_wallet_handler),
        ],
        HISTORY_MENU: [
            CallbackQueryHandler(view_transaction_history_handler, pattern="^history_.*$"),
            CallbackQueryHandler(wallet_command, pattern="^back_to_menu$"),
        ],
    },
    fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)],
)

# # Define ConversationHandler
# case_listing_handler = ConversationHandler(
#     entry_points=[CommandHandler("listing", listing_command)],
#     states={
#         CASE_DETAILS: [
#             CallbackQueryHandler(case_details_callback, pattern="^case_.*$"),
#             CallbackQueryHandler(
#                 pagination_callback, pattern="^(page_previous|page_next)$"
#             ),
#         ]
#     },
#     fallbacks=[CommandHandler("cancel", lambda update, context: END)],
# )

# Settings conversation handler  -- TODO: Completed
settings_handler = ConversationHandler(
    entry_points=[CommandHandler("settings", settings_command)],
    states={
        SETTINGS_MENU: [
            CallbackQueryHandler(settings_menu_callback, pattern="^(settings_language|settings_mobile|settings_close|setlang_)"),
        ],
        WAITING_FOR_MOBILE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setting_mobile),
        ],
        MOBILE_MANAGEMENT: [
            CallbackQueryHandler(settings_menu_callback, pattern="^(mobile_|remove_)"),
        ],
        MOBILE_VERIFICATION: [
            CallbackQueryHandler(settings_menu_callback, pattern="^(remove_|settings_mobile)"),
        ],
        CREATE_CASE_TAC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setting_tac),
        ],
      
        END: [CommandHandler("settings", settings_command)],
    },
    fallbacks=[CommandHandler("cancel", lambda update, context: ConversationHandler.END)],
)
# --- Application Setup ---


