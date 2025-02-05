from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from constants import (
    SELECT_LANG,
    CHOOSE_COUNTRY,
    SHOW_DISCLAIMER,
    CHOOSE_CITY,
    CHOOSE_ACTION,
    CHOOSE_WALLET_TYPE,
    NAME_WALLET,
    CREATE_CASE_NAME,
    CREATE_CASE_MOBILE,
    CREATE_CASE_TAC,
    CREATE_CASE_DISCLAIMER,
    CREATE_CASE_REWARD_AMOUNT,
    CREATE_CASE_PERSON_DETAILS,
    CREATE_CASE_SUBMIT,
    END,
    WALLET_MENU,
    SETTINGS_MENU,
    WAITING_FOR_MOBILE,
)
from handler.wallet import wallet_command, wallet_menu_callback
from utils import (
    start,
    select_lang_callback,
    choose_country,
    country_callback,
    show_disclaimer,
    disclaimer_callback,
    choose_city,
    city_callback,
    choose_action,
    action_callback,
    wallet_type_callback,
    wallet_name_handler,
    cancel,
    error_handler,
)

from handler.case import (
    handle_name,
    handle_mobile,
    handle_tac,
    show_disclaimer_2,
    disclaimer_2_callback,
    handle_reward_amount,
    handle_person_details,
    submit_case,
)
from settings import settings_command, settings_menu_callback, mobile_number_handler

# Main conversation handler
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
        CREATE_CASE_REWARD_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reward_amount)
        ],
        CREATE_CASE_PERSON_DETAILS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_person_details)
        ],
        CREATE_CASE_SUBMIT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, submit_case)
        ],
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
    map_to_parent={},
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
    map_to_parent={},
)
