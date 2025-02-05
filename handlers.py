from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import logging

# Import your text-getting function and other constants
from constants import (
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
    CREATE_CASE_PHOTO,
    CREATE_CASE_LAST_SEEN_LOCATION,
    CREATE_CASE_SEX,
    CREATE_CASE_AGE,
    CREATE_CASE_HAIR_COLOR,
    CREATE_CASE_EYE_COLOR,
    CREATE_CASE_HEIGHT,
    CREATE_CASE_WEIGHT,
    CREATE_CASE_DISTINCTIVE_FEATURES,
    CREATE_CASE_SUBMIT,
    END,
    WAITING_FOR_MOBILE,
    WALLET_MENU,
    SETTINGS_MENU,
)
from wallet import load_user_wallet
from utils import (
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
from handler.wallet import wallet_command, wallet_menu_callback
from handler.case import (
    handle_name,
    handle_mobile,
    handle_tac,
    show_disclaimer_2,
    disclaimer_2_callback,
    handle_reward_amount,
    submit_case,
)
from settings import settings_command, settings_menu_callback, mobile_number_handler

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Create Case Handlers (with separate states for each person detail) ---


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's name input."""
    user_id = update.effective_user.id
    name = update.message.text.strip()
    context.user_data["case"] = {"name": name}
    await update.message.reply_text(get_text(user_id, "enter_mobile"))
    return CREATE_CASE_MOBILE


async def handle_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's mobile number input."""
    user_id = update.effective_user.id
    mobile = update.message.text.strip()
    context.user_data["case"]["mobile"] = mobile
    await update.message.reply_text(get_text(user_id, "enter_tac"))
    # You might want to call an async SMS-sending function here.
    return CREATE_CASE_TAC


async def handle_tac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle TAC verification."""
    user_id = update.effective_user.id
    tac = update.message.text.strip()
    # Simulate TAC verification (replace with your actual logic)
    if tac == "123456":
        await update.message.reply_text(get_text(user_id, "tac_verified"))
        await show_disclaimer_2(update, context)
        return CREATE_CASE_DISCLAIMER
    else:
        await update.message.reply_text(get_text(user_id, "tac_invalid"))
        return CREATE_CASE_TAC


async def disclaimer_2_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle Disclaimer 2 agreement."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "agree":
        await query.edit_message_text(get_text(user_id, "enter_reward_amount"))
        return CREATE_CASE_REWARD_AMOUNT
    else:
        await query.edit_message_text(get_text(user_id, "disagree_end"))
        return END


async def handle_reward_amount(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the reward amount input."""
    user_id = update.effective_user.id
    try:
        reward = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text(get_text(user_id, "invalid_reward"))
        return CREATE_CASE_REWARD_AMOUNT

    if reward < 2:
        await update.message.reply_text(get_text(user_id, "insufficient_funds"))
        return CREATE_CASE_REWARD_AMOUNT
    context.user_data["case"]["reward"] = reward
    await update.message.reply_text(get_text(user_id, "enter_person_name"))
    return CREATE_CASE_PERSON_NAME


async def handle_person_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for the person's name (the case target)."""
    user_id = update.effective_user.id
    person_name = update.message.text.strip()
    context.user_data["case"]["person_name"] = person_name
    logger.info(f"User {user_id} entered person name: {person_name}")
    await update.message.reply_text(get_text(user_id, "relationship"))
    return CREATE_CASE_RELATIONSHIP


async def handle_relationship(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle input for relationship detail."""
    user_id = update.effective_user.id
    relationship = update.message.text.strip()
    context.user_data["case"]["relationship"] = relationship
    logger.info(f"User {user_id} entered relationship: {relationship}")
    await update.message.reply_text(get_text(user_id, "send_photo"))
    return CREATE_CASE_PHOTO


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo upload."""
    user_id = update.effective_user.id
    if not update.message.photo:
        await update.message.reply_text(get_text(user_id, "no_photo_found"))
        return CREATE_CASE_PHOTO
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"photos/{user_id}_photo.jpg"
    await photo_file.download_to_drive(photo_path)
    context.user_data["case"]["photo_path"] = photo_path
    logger.info(f"User {user_id} uploaded photo: {photo_path}")
    await update.message.reply_text(get_text(user_id, "last_seen_location"))
    return CREATE_CASE_LAST_SEEN_LOCATION


async def handle_last_seen_location(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle input for last seen location."""
    user_id = update.effective_user.id
    location = update.message.text.strip()
    context.user_data["case"]["last_seen_location"] = location
    logger.info(f"User {user_id} entered last seen location: {location}")
    await update.message.reply_text(get_text(user_id, "sex"))
    return CREATE_CASE_SEX


async def handle_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for sex."""
    user_id = update.effective_user.id
    sex = update.message.text.strip()
    context.user_data["case"]["sex"] = sex
    logger.info(f"User {user_id} entered sex: {sex}")
    await update.message.reply_text(get_text(user_id, "age"))
    return CREATE_CASE_AGE


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for age."""
    user_id = update.effective_user.id
    age = update.message.text.strip()
    context.user_data["case"]["age"] = age
    logger.info(f"User {user_id} entered age: {age}")
    await update.message.reply_text(get_text(user_id, "hair_color"))
    return CREATE_CASE_HAIR_COLOR


async def handle_hair_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for hair color."""
    user_id = update.effective_user.id
    hair_color = update.message.text.strip()
    context.user_data["case"]["hair_color"] = hair_color
    logger.info(f"User {user_id} entered hair color: {hair_color}")
    await update.message.reply_text(get_text(user_id, "eye_color"))
    return CREATE_CASE_EYE_COLOR


async def handle_eye_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for eye color."""
    user_id = update.effective_user.id
    eye_color = update.message.text.strip()
    context.user_data["case"]["eye_color"] = eye_color
    logger.info(f"User {user_id} entered eye color: {eye_color}")
    await update.message.reply_text(get_text(user_id, "height"))
    return CREATE_CASE_HEIGHT


async def handle_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for height."""
    user_id = update.effective_user.id
    height = update.message.text.strip()
    context.user_data["case"]["height"] = height
    logger.info(f"User {user_id} entered height: {height}")
    await update.message.reply_text(get_text(user_id, "weight"))
    return CREATE_CASE_WEIGHT


async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for weight."""
    user_id = update.effective_user.id
    weight = update.message.text.strip()
    context.user_data["case"]["weight"] = weight
    logger.info(f"User {user_id} entered weight: {weight}")
    await update.message.reply_text(get_text(user_id, "distinctive_features"))
    return CREATE_CASE_DISTINCTIVE_FEATURES


async def handle_distinctive_features(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle input for distinctive features."""
    user_id = update.effective_user.id
    features = update.message.text.strip()
    context.user_data["case"]["distinctive_features"] = features
    logger.info(f"User {user_id} entered distinctive features: {features}")
    await update.message.reply_text(get_text(user_id, "reason_for_finding"))
    return CREATE_CASE_SUBMIT


async def submit_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Submit the case."""
    user_id = update.effective_user.id
    case = context.user_data.get("case", {})
    # Generate a unique case number (you can improve this logic)
    case_no = f"CASE-{user_id}-{len(context.user_data)}"
    logger.info(f"User {user_id} submitted case: {case_no}")

    # Transfer reward to escrow wallet
    reward_amount = case.get("reward", 0)
    user_wallet = load_user_wallet(user_id)
    if user_wallet and user_wallet.get("balance_sol", 0) >= reward_amount:
        # Simulate transfer to escrow wallet
        user_wallet["balance_sol"] -= reward_amount
        await update.message.reply_text(get_text(user_id, "escrow_transfer"))
    else:
        await update.message.reply_text(
            get_text(user_id, "insufficient_wallet_balance")
        )
        return END

    # Notify user of successful submission
    await update.message.reply_text(
        get_text(user_id, "case_submitted").format(case_no=case_no)
    )
    return END


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
        CREATE_CASE_REWARD_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reward_amount)
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
    application.add_handler(wallet_conv_handler)
    application.add_handler(settings_conv_handler)

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
