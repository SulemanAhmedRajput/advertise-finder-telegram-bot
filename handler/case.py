from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ContextTypes,
)

from constants import (
    CREATE_CASE_DISCLAIMER,
    CREATE_CASE_MOBILE,
    CREATE_CASE_PERSON_DETAILS,
    CREATE_CASE_REWARD_AMOUNT,
    CREATE_CASE_TAC,
    END,
    get_text,
)
from wallet import load_user_wallet
import logging

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


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
    # await send_sms(mobile, "You are verified successfully as a person finder.")
    return CREATE_CASE_TAC


async def handle_tac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle TAC verification."""
    user_id = update.effective_user.id
    tac = update.message.text.strip()
    # Simulate TAC verification
    if tac == "123456":  # Replace with actual TAC verification logic
        await update.message.reply_text(get_text(user_id, "tac_verified"))
        await show_disclaimer_2(update, context)
        return CREATE_CASE_DISCLAIMER
    else:
        await update.message.reply_text(get_text(user_id, "tac_invalid"))
        return CREATE_CASE_TAC


async def show_disclaimer_2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show Disclaimer 2."""
    user_id = update.effective_user.id
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    get_text(user_id, "agree_btn"), callback_data="agree"
                )
            ],
            [
                InlineKeyboardButton(
                    get_text(user_id, "disagree_btn"), callback_data="disagree"
                )
            ],
        ]
    )
    await update.message.reply_text(
        get_text(user_id, "disclaimer_2"),
        reply_markup=kb,
    )
    return CREATE_CASE_DISCLAIMER


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
    reward = float(update.message.text.strip())
    if reward < 2:
        await update.message.reply_text(get_text(user_id, "insufficient_funds"))
        return CREATE_CASE_REWARD_AMOUNT
    context.user_data["case"]["reward"] = reward
    await update.message.reply_text(get_text(user_id, "enter_person_name"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_person_details(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle person details input."""
    user_id = update.effective_user.id
    person_name = update.message.text.strip()
    context.user_data["case"]["person_name"] = person_name

    logger.info(f"User {user_id} entered person_name: {person_name}")

    # Prompt for relationship
    await update.message.reply_text(get_text(user_id, "relationship"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_relationship(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    relationship = update.message.text.strip()
    context.user_data["case"]["relationship"] = relationship

    logger.info(f"User {user_id} entered relationship: {relationship}")

    await update.message.reply_text(get_text(user_id, "upload_photo"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"photos/{user_id}_photo.jpg"
    await photo_file.download_to_drive(photo_path)
    context.user_data["case"]["photo_path"] = photo_path

    logger.info(f"User {user_id} uploaded photo: {photo_path}")

    await update.message.reply_text(get_text(user_id, "last_seen_location"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_last_seen_location(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    location = update.message.text.strip()
    context.user_data["case"]["last_seen_location"] = location

    logger.info(f"User {user_id} entered last_seen_location: {location}")

    await update.message.reply_text(get_text(user_id, "sex"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    sex = update.message.text.strip()
    context.user_data["case"]["sex"] = sex

    logger.info(f"User {user_id} entered sex: {sex}")

    await update.message.reply_text(get_text(user_id, "age"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    age = update.message.text.strip()
    context.user_data["case"]["age"] = age

    logger.info(f"User {user_id} entered age: {age}")

    await update.message.reply_text(get_text(user_id, "hair_color"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_hair_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    hair_color = update.message.text.strip()
    context.user_data["case"]["hair_color"] = hair_color

    logger.info(f"User {user_id} entered hair_color: {hair_color}")

    await update.message.reply_text(get_text(user_id, "eye_color"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_eye_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    eye_color = update.message.text.strip()
    context.user_data["case"]["eye_color"] = eye_color

    logger.info(f"User {user_id} entered eye_color: {eye_color}")

    await update.message.reply_text(get_text(user_id, "height"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    height = update.message.text.strip()
    context.user_data["case"]["height"] = height

    logger.info(f"User {user_id} entered height: {height}")

    await update.message.reply_text(get_text(user_id, "weight"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    weight = update.message.text.strip()
    context.user_data["case"]["weight"] = weight

    logger.info(f"User {user_id} entered weight: {weight}")

    await update.message.reply_text(get_text(user_id, "distinctive_features"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_distinctive_features(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    features = update.message.text.strip()
    context.user_data["case"]["distinctive_features"] = features

    logger.info(f"User {user_id} entered distinctive_features: {features}")

    await update.message.reply_text(get_text(user_id, "reason_for_finding"))
    return CREATE_CASE_PERSON_DETAILS


async def submit_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Submit the case."""
    user_id = update.effective_user.id
    case = context.user_data.get("case", {})
    case_no = (
        f"CASE-{user_id}-{len(context.user_data)}"  # Generate a unique case number
    )

    logger.info(f"User {user_id} submitted case: {case_no}")

    # Transfer reward to escrow wallet
    reward_amount = case.get("reward", 0)
    user_wallet = load_user_wallet(user_id)
    if user_wallet and user_wallet.get("balance_sol", 0) >= reward_amount:
        # Simulate transfer to escrow wallet
        user_wallet["balance_sol"] -= reward_amount
        await update.message.reply_text(get_text(user_id, "escrow_transfer"))

    # Notify user of successful submission
    await update.message.reply_text(
        get_text(user_id, "case_submitted").format(case_no=case_no)
    )
    return END
