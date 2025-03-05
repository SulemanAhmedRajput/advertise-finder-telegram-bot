from handlers.case_handler import (
    disclaimer_2_callback,
    handle_age,
    handle_ask_reward_amount,
    handle_distinctive_features,
    handle_eye_color,
    handle_hair_color,
    handle_height,
    handle_last_seen_location,
    handle_new_mobile,
    handle_select_mobile,
    handle_name,
    handle_person_name,
    handle_photo,
    handle_reason_for_finding,
    handle_relationship,
    handle_sex,
    handle_tac,
    handle_transfer_confirmation,
    handle_weight,
)
from handlers.finder_handler import (
    handle_advertiser_response,
    handle_confirm_found,
    handle_enter_location,
    handle_extend_reward,
    handle_extend_reward_amount,
    handle_pagination,
    handle_wallet_selection,
    show_advertisements,
    case_details,
    handle_proof,
    handle_found_case,
    province_callback,
    choose_province,
)
from handlers.listing_handler import (
    ask_reward_amount,
    cancel_edit_callback,
    cancel_reward,
    case_details_callback,
    confirm_reward,
    delete_case_callback,
    edit_case_callback,
    edit_field_callback,
    listing_command,
    pagination_callback,
    process_reward_transfer,
    reward_case_callback,
    update_case_field,
)
from handlers.wallet_handler import (
    confirm_delete_wallet,
    create_wallet,
    delete_wallet,
    process_create_wallet,
    process_delete_wallet,
    refresh_wallets,
    select_wallet_type,
    show_address,
    show_specific_address,
    sol_wallets,
    usdt_wallets,
    view_history,
    view_specific_history,
    wallet_command,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
import logging

# Import your text-getting function and other constants
from constants import State
from constant.language_constant import get_text
from handlers.settings_handler import (
    handle_setting_mobile,
    handle_setting_tac,
    settings_command,
    settings_menu_callback,
)
from handlers.start_handler import (
    action_callback,
    choose_city,
    city_callback,
    start,
    select_lang_callback,
    choose_country,
    country_callback,
    disclaimer_callback,
    cancel,
    wallet_name_handler,
    wallet_selection_callback,
    wallet_type_callback,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Main conversation handler for the bot
start_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        State.SELECT_LANG: [
            CallbackQueryHandler(select_lang_callback, pattern="^lang_")
        ],
        State.CHOOSE_COUNTRY: [
            CallbackQueryHandler(
                country_callback, pattern="^(country_select_|country_page_)"
            ),
            MessageHandler(filters.TEXT & ~filters.COMMAND, choose_country),
        ],
        State.SHOW_DISCLAIMER: [
            CallbackQueryHandler(disclaimer_callback, pattern="^(agree|disagree)$")
        ],
        State.CHOOSE_CITY: [
            CallbackQueryHandler(city_callback, pattern="^(city_select_|city_page_)"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, choose_city),
        ],
        State.CHOOSE_ACTION: [
            CallbackQueryHandler(action_callback, pattern="^(advertise|find_people)$")
        ],
        State.CHOOSE_WALLET_TYPE: [
            CallbackQueryHandler(wallet_type_callback, pattern="^(SOL|USDT)$"),
            CallbackQueryHandler(wallet_selection_callback, pattern="^wallet_"),
            CallbackQueryHandler(
                wallet_name_handler, pattern="^create_new_wallet$"
            ),  # Handle create_new_wallet
        ],
        State.NAME_WALLET: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_name_handler),
        ],
        # Create Case Flow:
        State.CREATE_CASE_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)
        ],
        State.CREATE_CASE_MOBILE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_mobile)
        ],
        State.MOBILE_MANAGEMENT: [
            CallbackQueryHandler(
                handle_select_mobile, pattern="^(select_mobile_.*|mobile_add)$"
            ),
        ],
        State.CREATE_CASE_TAC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tac)
        ],
        State.CREATE_CASE_DISCLAIMER: [
            CallbackQueryHandler(disclaimer_2_callback, pattern="^(agree|disagree)$")
        ],
        State.CREATE_CASE_PERSON_NAME: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_person_name)
        ],
        State.CREATE_CASE_RELATIONSHIP: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_relationship)
        ],
        State.CREATE_CASE_PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
        State.CREATE_CASE_LAST_SEEN_LOCATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_last_seen_location)
        ],
        State.CREATE_CASE_SEX: [CallbackQueryHandler(handle_sex)],
        State.CREATE_CASE_AGE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)
        ],
        State.CREATE_CASE_HAIR_COLOR: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_hair_color)
        ],
        State.CREATE_CASE_EYE_COLOR: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_eye_color)
        ],
        State.CREATE_CASE_HEIGHT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_height)
        ],
        State.CREATE_CASE_WEIGHT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_weight)
        ],
        State.CREATE_CASE_DISTINCTIVE_FEATURES: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_distinctive_features)
        ],
        State.CREATE_CASE_ASK_REASON: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reason_for_finding)
        ],
        State.CREATE_CASE_ASK_REWARD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ask_reward_amount)
        ],
        State.CREATE_CASE_CONFIRM_TRANSFER: [
            CallbackQueryHandler(
                handle_transfer_confirmation,
                pattern="^(confirm_transfer|cancel_transfer)$",
            )
        ],
        # From here the finder is the one who is going to find the person
        State.CHOOSE_PROVINCE: [
            CallbackQueryHandler(
                province_callback, pattern="^(province_select_|province_page_)"
            ),
            MessageHandler(filters.TEXT & ~filters.COMMAND, choose_province),
        ],
        State.CASE_LIST: [
            CallbackQueryHandler(show_advertisements, pattern=r"^page_(previous|next)"),
            CallbackQueryHandler(case_details, pattern=r"^case_"),
            CallbackQueryHandler(show_advertisements, pattern="^back_to_list"),
        ],
        State.CASE_DETAILS: [
            CallbackQueryHandler(handle_pagination, pattern="^case_page_"),
            CallbackQueryHandler(case_details, pattern="^case_"),
            CallbackQueryHandler(handle_found_case, pattern="^found_"),
            CallbackQueryHandler(show_advertisements, pattern="^back_to_list"),
        ],
        State.UPLOAD_PROOF: [
            MessageHandler(filters.PHOTO | filters.VIDEO, handle_proof)
        ],
        State.ENTER_LOCATION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_enter_location)
        ],
        State.EXTEND_REWARD: [
            CallbackQueryHandler(
                handle_extend_reward, pattern="^(yes_extend|no_extend)$"
            )
        ],
        State.EXTEND_REWARD_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_extend_reward_amount)
        ],
        State.ADVERTISER_RESPONSE: [
            CallbackQueryHandler(
                handle_advertiser_response, pattern="^(accept_extend|reject_extend)$"
            )
        ],
        State.SELECT_WALLET: [
            CallbackQueryHandler(
                handle_wallet_selection,
                pattern="^(select_extend_wallet_|create_extend_wallet)",
            )
        ],
        State.TRANSFER_CONFIRMATION: [
            CallbackQueryHandler(
                handle_transfer_confirmation,
                pattern="^(confirm_transfer|cancel_transfer)$",
            )
        ],
        State.CONFIRM_FOUND: [
            CallbackQueryHandler(
                handle_confirm_found, pattern="^(confirm_found|cancel_found)$"
            )
        ],
        State.END: [CommandHandler("start", start)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)

# Wallet conversation handler
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

# Define conversation handler
wallet_handler = ConversationHandler(
    entry_points=[CommandHandler("wallet", wallet_command)],
    states={
        State.WALLET_MENU: [
            CallbackQueryHandler(refresh_wallets, pattern="^refresh_wallets$"),
            CallbackQueryHandler(sol_wallets, pattern="^sol_wallets$"),
            CallbackQueryHandler(usdt_wallets, pattern="^usdt_wallets$"),
            CallbackQueryHandler(show_address, pattern="^show_address$"),
            CallbackQueryHandler(view_history, pattern="^view_history$"),
            CallbackQueryHandler(
                create_wallet, pattern="^create_wallet$"
            ),  # Entry point for wallet creation
            CallbackQueryHandler(delete_wallet, pattern="^delete_wallet$"),
        ],
        State.SHOW_ADDRESS: [
            CallbackQueryHandler(show_specific_address, pattern="^show_address_"),
        ],
        State.VIEW_HISTORY: [
            CallbackQueryHandler(view_specific_history, pattern="^view_history_"),
        ],
        State.SELECT_WALLET_TYPE: [
            CallbackQueryHandler(
                select_wallet_type, pattern="^(USDT|SOL)$"
            ),  # Handle wallet type selection
        ],
        State.ENTER_WALLET_NAME: [
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, process_create_wallet
            ),  # Handle wallet name input
        ],
        State.CONFIRM_DELETE_WALLET: [
            CallbackQueryHandler(
                confirm_delete_wallet, pattern="^confirm_delete_wallet_"
            ),
        ],
        State.DELETE_WALLET: [
            CallbackQueryHandler(process_delete_wallet, pattern="^delete_wallet_"),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)


listing_handler = ConversationHandler(
    entry_points=[CommandHandler("listing", listing_command)],
    states={
        State.CASE_DETAILS: [
            CallbackQueryHandler(case_details_callback, pattern="^case_.*$"),
            CallbackQueryHandler(
                pagination_callback, pattern="^(page_previous|page_next)$"
            ),
            CallbackQueryHandler(edit_field_callback, pattern="^edit_field_.*$"),
            CallbackQueryHandler(edit_case_callback, pattern="^edit_.*$"),
            CallbackQueryHandler(cancel_edit_callback, pattern="^cancel_edit$"),
            CallbackQueryHandler(delete_case_callback, pattern="^delete_.*$"),
            CallbackQueryHandler(reward_case_callback, pattern="^reward_.*$"),
            CallbackQueryHandler(ask_reward_amount, pattern="^send_reward_.*$"),
        ],
        State.EDIT_FIELD: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, process_reward_transfer)
        ],
        State.CONFIRM_REWARD: [  # New state for confirmation
            CallbackQueryHandler(confirm_reward, pattern="^confirm_reward$"),
            CallbackQueryHandler(cancel_reward, pattern="^cancel_reward$"),
        ],
    },
    fallbacks=[
        CommandHandler("cancel", lambda update, context: State.END),
    ],
    allow_reentry=True,
)


# Settings conversation handler  -- TODO: Completed
settings_handler = ConversationHandler(
    entry_points=[CommandHandler("settings", settings_command)],
    states={
        State.SETTINGS_MENU: [
            CallbackQueryHandler(
                settings_menu_callback,
                pattern="^(settings_language|settings_mobile|settings_close|setlang_)",
            ),
        ],
        State.WAITING_FOR_MOBILE: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setting_mobile),
        ],
        State.MOBILE_MANAGEMENT: [
            CallbackQueryHandler(settings_menu_callback, pattern="^(mobile_|remove_)"),
        ],
        State.MOBILE_VERIFICATION: [
            CallbackQueryHandler(
                settings_menu_callback, pattern="^(remove_|settings_mobile)"
            ),
        ],
        State.CREATE_CASE_TAC: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_setting_tac),
        ],
        State.END: [CommandHandler("settings", settings_command)],
    },
    fallbacks=[CommandHandler("cancel", lambda update, context: State.END)],
    allow_reentry=True,
)
# --- Application Setup ---
