from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from constants import (
    CREATE_CASE_TAC,
    END,
    MOBILE_MANAGEMENT,
    MOBILE_VERIFICATION,
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

from services.user_service import get_user_mobiles, save_user_lang, save_user_mobiles, validate_mobile
from utils.helper import generate_tac



# Handlers
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /settings command - shows an inline menu."""
    user_id = update.effective_user.id
    kb = [
        [InlineKeyboardButton(get_text(user_id, "btn_language"), callback_data="settings_language")],
        [InlineKeyboardButton(get_text(user_id, "btn_mobile_number"), callback_data="settings_mobile")],
        [InlineKeyboardButton(get_text(user_id, "btn_close_menu"), callback_data="settings_close")],
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
        # Language selection
        kb = [
            [InlineKeyboardButton(LANG_DATA["en"]["lang_button"], callback_data="setlang_en")],
            [InlineKeyboardButton(LANG_DATA["zh"]["lang_button"], callback_data="setlang_zh")],
        ]
        await query.edit_message_text(
            text="Choose your preferred language:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML",
        )
        return SETTINGS_MENU

    elif choice == "settings_mobile":
        # Mobile management
        mobiles = await get_user_mobiles(user_id)
        if not mobiles:
            await query.edit_message_text(
                get_text(user_id, "enter_mobile"), parse_mode="HTML"
            )
            return WAITING_FOR_MOBILE
        else:
            # Show saved mobile numbers
            kb = [
                [InlineKeyboardButton(f"📱 {mobile}", callback_data=f"mobile_{mobile}")]
                for mobile in mobiles
            ]
            kb.append([InlineKeyboardButton("➕ Add New", callback_data="mobile_add")])
            await query.edit_message_text(
                "Your saved mobile numbers:",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="HTML",
            )
            return MOBILE_MANAGEMENT

    elif choice == "settings_close":
        # Close the menu
        await query.edit_message_text(
            get_text(user_id, "btn_close_menu"), parse_mode="HTML"
        )
        return END

    elif choice.startswith("setlang_"):
        new_lang = choice.replace("setlang_", "")
        await save_user_lang(user_id, new_lang)
        context.user_data["lang"] = new_lang
        if user_id not in user_data_store:
            user_data_store[user_id] = {}
        user_data_store[user_id]["lang"] = new_lang
        await query.edit_message_text(
            get_text(user_id, "lang_updated"), parse_mode="HTML"
        )
        return END

    elif choice.startswith("mobile_"):
        mobile = choice.replace("mobile_", "")
        if mobile == "add":
            await query.edit_message_text(
                get_text(user_id, "enter_mobile"), parse_mode="HTML"
            )
            return WAITING_FOR_MOBILE
        else:
            # Options for selected mobile
            kb = [
                [InlineKeyboardButton("❌ Remove", callback_data=f"remove_{mobile}")],
                [InlineKeyboardButton("🔙 Back", callback_data="settings_mobile")],
            ]
            await query.edit_message_text(
                f"Selected mobile: {mobile}\nWhat would you like to do?",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="HTML",
            )
            return MOBILE_VERIFICATION

    elif choice.startswith("remove_"):
        mobile = choice.replace("remove_", "")
        mobiles = await get_user_mobiles(user_id)
        if mobile in mobiles:
            mobiles.remove(mobile)
            await save_user_mobiles(user_id, mobiles)
            await query.edit_message_text(
                f"✅ Removed mobile: {mobile}", parse_mode="HTML"
            )
        else:
            await query.edit_message_text(
                f"❌ Mobile number not found: {mobile}", parse_mode="HTML"
            )
        return MOBILE_MANAGEMENT

    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return END

async def handle_setting_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the user's mobile number input."""
    user_id = update.effective_user.id
    mobile = update.message.text.strip()

    # Validate mobile number
    if not validate_mobile(mobile):
        await update.message.reply_text(get_text(user_id, "invalid_mobile_number"))
        return WAITING_FOR_MOBILE

    # Generate TAC
    tac = generate_tac()
    context.user_data["tac"] = tac
    context.user_data["mobile"] = mobile

    # Save TAC and mobile in user data store
    if user_id not in user_data_store:
        user_data_store[user_id] = {}
    user_data_store[user_id]["tac"] = tac
    user_data_store[user_id]["mobile"] = mobile

    # Simulate sending TAC via SMS
    print(f"Sending TAC {tac} to mobile {mobile}")

    # Prompt user to enter TAC
    await update.message.reply_text(get_text(user_id, "enter_tac"))
    return CREATE_CASE_TAC

    
async def handle_setting_tac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle TAC verification."""
    user_id = update.effective_user.id
    user_tac = update.message.text.strip()
    stored_tac = context.user_data.get("tac")
    mobile = context.user_data.get("mobile")

    print(f"Getting the number which is: {mobile}")

    # Verify TAC
    if user_tac == stored_tac:
        # Save the verified mobile number
        mobiles = await get_user_mobiles(user_id)
        if mobile not in mobiles:
            mobiles.append(mobile)
            await save_user_mobiles(user_id, mobiles)

        # Show the list of saved mobile numbers
        kb = [
            [InlineKeyboardButton(f"📱 {number}", callback_data=f"mobile_{number}")]
            for number in mobiles
        ]
        kb.append([InlineKeyboardButton("➕ Add New", callback_data="mobile_add")])

        await update.message.reply_text(
            "✅ Mobile number verified and saved successfully!\nYour saved mobile numbers:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML",
        )
        return MOBILE_MANAGEMENT

    else:
        await update.message.reply_text(get_text(user_id, "tac_invalid"))
        return CREATE_CASE_TAC