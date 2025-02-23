import re
from config.config_manager import STAKE_WALLET_PUBLIC_KEY
from constant.language_constant import get_text, user_data_store
from models.case_model import Case
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
)
import logging

from constants import (
    State,
)
from models.mobile_number_model import MobileNumber
from services.case_service import get_drafted_case_wallet, update_or_create_case
from services.wallet_service import WalletService
import utils.cloudinary
from utils.twilio import generate_tac
from utils.wallet import load_user_wallet
from utils.cloudinary import upload_image
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction
from solders.message import Message
from models.wallet_model import Wallet
from services.user_service import get_user_mobiles, save_user_mobiles, validate_mobile


client = Client("https://api.devnet.solana.com")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Create Case Handlers (with separate states for each person detail) ---


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's name input."""
    user_id = update.effective_user.id
    name = update.message.text.strip()
    await update_or_create_case(user_id, name=name)
    context.user_data["case"] = {"name": name}

    # Check if the user has existing mobile numbers
    existing_mobiles = await get_user_mobiles(user_id)

    if existing_mobiles:
        # Show existing mobile numbers with an option to select one
        kb = [
            [InlineKeyboardButton(mobile, callback_data=f"select_mobile_{mobile}")]
            for mobile in existing_mobiles
        ]
        kb.append([InlineKeyboardButton("➕ Add New", callback_data="mobile_add")])
        await update.message.reply_text(
            get_text(user_id, "choose_existing_mobile"),
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return State.MOBILE_MANAGEMENT
    else:
        # Ask for a new mobile number if none exists
        await update.message.reply_text(get_text(user_id, "enter_mobile"))
        return State.CREATE_CASE_MOBILE


async def handle_select_mobile(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the selection of an existing mobile number or adding a new one."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "mobile_add":
        # Handle 'Add New' click: Ask the user to input a new mobile number
        await query.edit_message_text(get_text(user_id, "enter_mobile"))
        return State.CREATE_CASE_MOBILE  # Transition to state for mobile number input
    else:
        selected_mobile = query.data.replace("select_mobile_", "")

        # Fetch the MobileNumber reference from the database
        mobile_number = await MobileNumber.find_one({"number": selected_mobile})

        if not mobile_number:
            await query.edit_message_text(
                "The selected mobile number does not exist in the database. Please try again."
            )
            return State.CREATE_CASE_MOBILE

        # Store the mobile number reference in user_data for further use
        context.user_data["mobile"] = selected_mobile
        context.user_data["selected_number"] = (
            selected_mobile  # Save the MobileNumber reference
        )

        tac = generate_tac()  # Generate TAC for the selected mobile number
        context.user_data["tac"] = tac

        print("TAC:", tac)

        # Notify the user that the mobile number was selected
        await query.edit_message_text(
            f"Selected mobile number: {selected_mobile} - A TAC is sent to you on this number"
        )

        # Proceed to the next step
        await query.message.reply_text(get_text(user_id, "enter_tac"))
        return State.CREATE_CASE_TAC


async def handle_new_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the input of a new mobile number."""
    user_id = update.effective_user.id
    mobile_number = update.message.text.strip()

    if re.match(r"^\+?\d{10,15}$", mobile_number):  # Basic validation for mobile number
        context.user_data["mobile"] = mobile_number

        context.user_data["selected_number"] = mobile_number
        # Update or create the case with the new mobile number
        print(f"Mobile number: {mobile_number}")

        tac = generate_tac()  # Generate TAC for the new mobile number
        context.user_data["tac"] = tac
        print(f"Tac are: {tac}")

        await update.message.reply_text(
            f"Mobile number {mobile_number} added. A TAC has been sent to your number."
        )

        # Proceed to the next step: Enter the TAC
        await update.message.reply_text(get_text(user_id, "enter_tac"))
        return State.CREATE_CASE_TAC
    else:
        # If invalid, prompt the user to enter a valid mobile number format
        await update.message.reply_text(get_text(user_id, "enter_valid_mobile"))
        return State.CREATE_CASE_MOBILE


async def handle_tac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle TAC verification."""
    user_id = update.effective_user.id
    user_tac = update.message.text.strip()
    stored_tac = context.user_data.get("tac")
    selected_number = context.user_data.get(
        "selected_number"
    )  # Get the mobile number reference

    if user_tac == stored_tac:
        await update.message.reply_text(get_text(user_id, "tac_verified"))

        # After TAC verification, update the case with the mobile reference
        await update_or_create_case(user_id, mobile=selected_number)

        # Proceed to the next step
        await show_disclaimer_2(update, context)
        return State.CREATE_CASE_DISCLAIMER
    else:
        await update.message.reply_text(get_text(user_id, "tac_invalid"))
        return State.CREATE_CASE_TAC


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
    await update.message.reply_text(get_text(user_id, "disclaimer_2"), reply_markup=kb)
    return State.CREATE_CASE_DISCLAIMER


async def disclaimer_2_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle Disclaimer 2 agreement."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "agree":

        await query.edit_message_text("Please enter the person's name.")
        return State.CREATE_CASE_PERSON_NAME
    else:
        await query.edit_message_text(get_text(user_id, "disagree_end"))
        return State.END


async def handle_person_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for the person's name (the case target)."""
    user_id = update.effective_user.id
    person_name = update.message.text.strip()
    await update_or_create_case(user_id, person_name=person_name)
    context.user_data["case"]["person_name"] = person_name
    logger.info(f"User {user_id} entered person name: {person_name}")
    await update.message.reply_text(get_text(user_id, "relationship"))
    return State.CREATE_CASE_RELATIONSHIP


async def handle_relationship(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle input for relationship detail."""
    user_id = update.effective_user.id
    relationship = update.message.text.strip()
    await update_or_create_case(user_id, relationship=relationship)
    context.user_data["case"]["relationship"] = relationship
    logger.info(f"User {user_id} entered relationship: {relationship}")

    await update.message.reply_text(get_text(user_id, "upload_photo"))
    return State.CREATE_CASE_PHOTO


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo upload and store it on Cloudinary."""
    user_id = update.effective_user.id

    # Check if the user sent a photo
    if not update.message.photo:
        await update.message.reply_text(get_text(user_id, "no_photo_found"))
        return State.CREATE_CASE_PHOTO

    # Get the highest quality photo from the list (the last element)
    photo_file = await update.message.photo[-1].get_file()

    # Define the absolute path for the photos directory
    photo_dir = os.path.join(os.getcwd(), "photos")

    # Create the directory if it doesn't exist
    os.makedirs(photo_dir, exist_ok=True)

    # Define the path to save the photo
    photo_path = os.path.join(photo_dir, f"{user_id}_photo.jpg")

    # Debug log for the path
    logger.info(f"Saving photo at path: {photo_path}")

    # Download the photo to the server
    await photo_file.download_to_drive(photo_path)

    # Upload the photo to Cloudinary
    upload_result = await upload_image(photo_path)
    if upload_result:
        logger.info(f"Uploaded Photo URL: {upload_result}")

        await update_or_create_case(user_id, case_photo=upload_result)
        context.user_data["case"][
            "photo_url"
        ] = upload_result  # Store URL instead of local path

    # Move to the next step (e.g., last seen location)
    await update.message.reply_text(get_text(user_id, "last_seen_location"))
    return State.CREATE_CASE_LAST_SEEN_LOCATION


async def handle_last_seen_location(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle input for last seen location."""
    user_id = update.effective_user.id
    location = update.message.text.strip()
    await update_or_create_case(user_id, last_seen_location=location)
    context.user_data["case"]["last_seen_location"] = location
    logger.info(f"User {user_id} entered last seen location: {location}")

    # Provide options for sex
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Male", callback_data="male"),
                InlineKeyboardButton("Female", callback_data="female"),
            ],
            [
                InlineKeyboardButton("Other", callback_data="other"),
            ],
        ]
    )
    await update.message.reply_text(get_text(user_id, "sex"), reply_markup=kb)
    return State.CREATE_CASE_SEX


async def handle_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for sex."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    sex = query.data
    await update_or_create_case(user_id, gender=sex)
    context.user_data["case"]["sex"] = sex
    logger.info(f"User {user_id} selected sex: {sex}")
    await query.edit_message_text(get_text(user_id, "age"))
    return State.CREATE_CASE_AGE


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for age."""
    user_id = update.effective_user.id
    age = update.message.text.strip()

    if not age.isdigit():
        await update.message.reply_text("Please enter a valid number for age.")
        return State.CREATE_CASE_AGE

    await update_or_create_case(user_id, age=age)
    context.user_data["case"]["age"] = age
    logger.info(f"User {user_id} entered age: {age}")
    await update.message.reply_text(get_text(user_id, "hair_color"))
    return State.CREATE_CASE_HAIR_COLOR


async def handle_hair_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for hair color."""
    user_id = update.effective_user.id
    hair_color = update.message.text.strip()
    await update_or_create_case(user_id, hair_color=hair_color)
    context.user_data["case"]["hair_color"] = hair_color
    logger.info(f"User {user_id} entered hair color: {hair_color}")
    await update.message.reply_text(get_text(user_id, "eye_color"))
    return State.CREATE_CASE_EYE_COLOR


async def handle_eye_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for eye color."""
    user_id = update.effective_user.id
    eye_color = update.message.text.strip()
    await update_or_create_case(user_id, eye_color=eye_color)
    context.user_data["case"]["eye_color"] = eye_color
    logger.info(f"User {user_id} entered eye color: {eye_color}")
    await update.message.reply_text(get_text(user_id, "height"))
    return State.CREATE_CASE_HEIGHT


async def handle_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for height."""
    user_id = update.effective_user.id
    height = update.message.text.strip()

    if not height.isdigit():
        await update.message.reply_text("Please enter a valid number for height.")
        return State.CREATE_CASE_HEIGHT

    await update_or_create_case(user_id, height=height)
    context.user_data["case"]["height"] = height
    logger.info(f"User {user_id} entered height: {height}")
    await update.message.reply_text(get_text(user_id, "weight"))
    return State.CREATE_CASE_WEIGHT


async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for weight."""
    user_id = update.effective_user.id
    weight = update.message.text.strip()

    if not weight.isdigit():
        await update.message.reply_text("Please enter a valid number for weight.")
        return State.CREATE_CASE_WEIGHT

    await update_or_create_case(user_id, weight=weight)
    context.user_data["case"]["weight"] = weight
    logger.info(f"User {user_id} entered weight: {weight}")
    await update.message.reply_text(get_text(user_id, "distinctive_features"))
    return State.CREATE_CASE_DISTINCTIVE_FEATURES


async def handle_distinctive_features(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle input for distinctive features."""
    user_id = update.effective_user.id
    features = update.message.text.strip()

    await update_or_create_case(user_id, distinctive_features=features)
    context.user_data["case"]["distinctive_features"] = features
    logger.info(f"User {user_id} entered distinctive features: {features}")
    await update.message.reply_text(get_text(user_id, "reason_for_finding"))
    return State.CREATE_CASE_SUBMIT  # Transition to the next state


async def handle_reason_for_finding(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle input for reason for finding."""
    user_id = update.effective_user.id
    reason = update.message.text.strip()

    await update.message.reply_text("Case Submitted")
    await update.message.reply_text(get_text(user_id, "enter_reward_amount"))
    return State.CREATE_CASE_ASK_REWARD


async def handle_ask_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for the reward amount depending on the wallet type."""
    user_id = update.effective_user.id
    try:
        reward_amount = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Please enter a valid amount for the reward.")
        return State.CREATE_CASE_ASK_REWARD

    user_wallet = await get_drafted_case_wallet(
        user_id
    ) or await WalletService.create_wallet(
        user_id, wallet_type="SOL", wallet_name="Default Wallet"
    )

    if user_wallet and reward_amount >= 1:
        context.user_data["reward_amount"] = reward_amount
        await update.message.reply_text(
            f"Your reward of {reward_amount} SOL is valid. Proceeding to confirm the transfer."
        )
        return await handle_transfer_confirmation(update, context)

    await update.message.reply_text(
        "Minimum reward amount is 1 SOL. Please enter a higher amount."
    )
    return State.CREATE_CASE_ASK_REWARD


async def handle_transfer_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the user's transfer confirmation."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    reward_amount = context.user_data.get("reward_amount")

    if not reward_amount:
        await query.edit_message_text(
            "Reward amount not found. Please restart the process."
        )
        return State.CREATE_CASE_ASK_REWARD

    confirm_kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✔️ Confirm Transfer", callback_data="confirm_transfer"
                ),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_transfer"),
            ]
        ]
    )

    await query.edit_message_text(
        f"Do you want to transfer {reward_amount} SOL to the owner's account?",
        reply_markup=confirm_kb,
    )
    return State.CREATE_CASE_CONFIRM_TRANSFER


async def transfer_to_owner(user_id: int, reward_amount: float) -> bool:
    """Transfer SOL to the owner's account."""
    user_wallet = await Wallet.find_one({"user_id": user_id})
    if not user_wallet:
        return False

    owner_public_key = Pubkey.from_string(STAKE_WALLET_PUBLIC_KEY)
    transfer_params = TransferParams(
        from_pubkey=Pubkey.from_string(user_wallet["public_key"]),
        to_pubkey=owner_public_key,
        lamports=int(reward_amount * 1e9),
    )
    transaction = Transaction().add(transfer(transfer_params))

    try:
        result = await client.send_transaction(
            transaction, Keypair.from_secret_key(bytes(user_wallet["private_key"]))
        )
        return result.get("result", False)
    except Exception as e:
        logger.error(f"SOL Transfer failed: {e}")
        return False
