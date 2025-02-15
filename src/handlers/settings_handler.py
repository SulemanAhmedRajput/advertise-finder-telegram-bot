from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from constants import (
    END,
    get_text,
    LANG_DATA,
    SETTINGS_MENU,
    user_data_store,
    WAITING_FOR_MOBILE,
)
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
)

from services.user_service import save_user_lang


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /settings command - shows an inline menu."""
    user_id = update.effective_user.id
    kb = [
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_language"), callback_data="settings_language"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_mobile_number"), callback_data="settings_mobile"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_close_menu"), callback_data="settings_close"
            )
        ],
    ]
    await update.message.reply_text(
        get_text(user_id, "menu_settings_title"),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode="HTML",
    )
    return SETTINGS_MENU


async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the settings menu actions."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    choice = query.data

    if choice == "settings_language":
        # Let’s reuse the language selection inline keyboard.
        kb = [
            [
                InlineKeyboardButton(
                    LANG_DATA["en"]["lang_button"], callback_data="setlang_en"
                ),
                InlineKeyboardButton(
                    LANG_DATA["zh"]["lang_button"], callback_data="setlang_zh"
                ),
            ]
        ]
        await query.edit_message_text(
            text="Choose your preferred language:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML",
        )
        return SETTINGS_MENU

    elif choice == "settings_mobile":
        # Ask user to enter their mobile number
        await query.edit_message_text(
            get_text(user_id, "enter_mobile"), parse_mode="HTML"
        )
        return WAITING_FOR_MOBILE

    elif choice == "settings_close":
        # Close the menu
        await query.edit_message_text(
            get_text(user_id, "btn_close_menu"), parse_mode="HTML"
        )
        return END

    # Handling the dynamic callback for language changes
    elif choice.startswith("setlang_"):
        new_lang = choice.replace("setlang_", "")
        if new_lang:
            await save_user_lang(user_id, new_lang)
        
        print(user_id)
        context.user_data["lang"] = new_lang
        if user_id not in user_data_store:
            user_data_store[user_id] = {}
        user_data_store[user_id]["lang"] = new_lang
        print("User data", user_data_store)
        await query.edit_message_text(
            get_text(user_id, "lang_updated"), parse_mode="HTML"
        )
        return END

    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return END


async def mobile_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive the user's mobile number and store it."""
    user_id = update.effective_user.id
    mobile = update.message.text.strip()
    user_data_store[user_id]["mobile_number"] = mobile
    msg = get_text(user_id, "mobile_saved").format(number=mobile)
    await update.message.reply_text(msg, parse_mode="HTML")
    return END
