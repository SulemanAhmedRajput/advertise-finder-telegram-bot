from models.case_model import Case
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
)
import logging

# Import your text-getting function and other constants
from constants import (
    CREATE_CASE_PHOTO,
    CREATE_CASE_REWARD_TYPE,
    CREATE_CASE_SUBMIT,
    ENTER_PRIVATE_KEY,
    TRANSFER_CONFIRMATION,
    get_text,
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
)
from utils.twilio import generate_tac, send_sms, verify_tac
from utils.wallet import load_user_wallet, transfer_solana_funds

from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction
from solders.message import Message

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
    context.user_data["case"] = {"name": name}
    await update.message.reply_text(get_text(user_id, "enter_mobile"))
    return CREATE_CASE_MOBILE


async def handle_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's mobile number input."""
    user_id = update.effective_user.id
    mobile = update.message.text.strip()

    # Generate and send TAC
    tac = generate_tac()  # Implement this function to generate a random TAC
    context.user_data["tac"] = tac
    context.user_data["mobile"] = mobile

    # Send TAC via Twilio
    message = send_sms(mobile, tac)

    await update.message.reply_text(get_text(user_id, "enter_tac"))
    return CREATE_CASE_TAC


async def handle_tac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle TAC verification."""
    user_id = update.effective_user.id
    user_tac = update.message.text.strip()
    stored_tac = context.user_data.get("tac")

    # if user_tac == stored_tac:
    if user_tac == "123456":
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
    await update.message.reply_text(get_text(user_id, "disclaimer_2"), reply_markup=kb)
    return CREATE_CASE_DISCLAIMER


async def disclaimer_2_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle Disclaimer 2 agreement."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "agree":
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        get_text(user_id, "sol_wallet"), callback_data="SOL"
                    ),
                    InlineKeyboardButton(
                        get_text(user_id, "btc_wallet"), callback_data="BTC"
                    ),
                ]
            ]
        )
        await query.edit_message_text(
            get_text(user_id, "account_wallet_type"), reply_markup=kb
        )
        return CREATE_CASE_REWARD_TYPE
    else:
        await query.edit_message_text(get_text(user_id, "disagree_end"))
        return END


# First handler to ask for the type (Solana or BTC)
async def handle_reward_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    logger.info(f"Reward type selected: {query.data}")  # Debugging line
    if query.data == "SOL":
        await query.edit_message_text(
            get_text(user_id, "enter_reward_amount"), parse_mode="HTML"
        )
        return CREATE_CASE_REWARD_AMOUNT
    elif query.data == "BTC":
        await query.edit_message_text(get_text(user_id, "btc_dev"), parse_mode="HTML")
        return END
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return END


# Handler for reward amount
async def handle_reward_amount(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    try:
        reward = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid amount, please enter a valid number.")
        return CREATE_CASE_REWARD_AMOUNT

    if reward < 2:
        await update.message.reply_text("The amount must be at least 2.")
        return CREATE_CASE_REWARD_AMOUNT

    context.user_data["case"]["reward"] = reward

    await update.message.reply_text("Please enter the person's name.")
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
    # await update.message.reply_text(get_text(user_id, "send_photo"))

    await update.message.reply_text(get_text(user_id, "upload_photo"))
    return CREATE_CASE_PHOTO
    # return CREATE_CASE_LAST_SEEN_LOCATION


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle photo upload."""
    user_id = update.effective_user.id

    # Check if the user sent a photo
    if not update.message.photo:
        await update.message.reply_text(get_text(user_id, "no_photo_found"))
        return CREATE_CASE_PHOTO

    # Get the highest quality photo from the list (the last element in the list)
    photo_file = await update.message.photo[-1].get_file()

    # Define the absolute path for the photos directory
    photo_dir = os.path.join(os.getcwd(), "photos")  # Ensure absolute path

    # Create the directory if it doesn't exist
    if not os.path.exists(photo_dir):
        os.makedirs(photo_dir)

    # Define the path to save the photo
    photo_path = os.path.join(photo_dir, f"{user_id}_photo.jpg")

    # Debug log for the path
    logger.info(f"Saving photo at path: {photo_path}")

    # Download the photo to the server
    await photo_file.download_to_drive(photo_path)

    # Store the photo path in user data for further processing
    context.user_data["case"]["photo_path"] = photo_path
    logger.info(f"User {user_id} uploaded photo: {photo_path}")

    # Move to the next step (e.g., last seen location)
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

    # Provide options for sex
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Male", callback_data="male"),
                InlineKeyboardButton("Female", callback_data="female"),
            ],
            [
                InlineKeyboardButton("Transgender", callback_data="transgender"),
                InlineKeyboardButton("Neutral", callback_data="neutral"),
            ],
        ]
    )
    await update.message.reply_text(get_text(user_id, "sex"), reply_markup=kb)
    return CREATE_CASE_SEX

    async def handle_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle input for sex."""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        sex = query.data
        context.user_data["case"]["sex"] = sex
        logger.info(f"User {user_id} selected sex: {sex}")
        await query.edit_message_text(get_text(user_id, "age"))
        return CREATE_CASE_AGE


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle input for age."""
    user_id = update.effective_user.id
    age = update.message.text.strip()

    if not age.isdigit():
        await update.message.reply_text("Please enter a valid number for age.")
        return CREATE_CASE_AGE

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

        if not height.isdigit():
            await update.message.reply_text("Please enter a valid number for height.")
            return CREATE_CASE_HEIGHT

        context.user_data["case"]["height"] = height
        logger.info(f"User {user_id} entered height: {height}")
        await update.message.reply_text(get_text(user_id, "weight"))
        return CREATE_CASE_WEIGHT

    async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle input for weight."""
        user_id = update.effective_user.id
        weight = update.message.text.strip()

        if not weight.isdigit():
            await update.message.reply_text("Please enter a valid number for weight.")
            return CREATE_CASE_WEIGHT

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
    return CREATE_CASE_SUBMIT  # Transition to the next state


async def handle_reason_for_finding(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle input for reason for finding."""
    user_id = update.effective_user.id
    reason = update.message.text.strip()
    # context.user_data["case"]["reason_for_finding"] = reason
    # logger.info(f"User {user_id} entered reason for finding: {reason}")

    # Submit the case and notify the user
    case_no = "CASE123456"  # Replace with actual case submission logic
    await update.message.reply_text(
        get_text(user_id, "case_submitted").format(case_no=case_no)
    )

    return await transfer_sol(update, context)


async def transfer_sol(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    # Ask the user for their private key to initiate the transaction
    await update.message.reply_text(
        "⚠️ Warning: Entering your private key here is insecure. "
        "Please ensure you trust this service before proceeding.\n\n"
        "To complete the transfer, please provide your Solana private key."
    )
    # Change the state to enter the private key
    return ENTER_PRIVATE_KEY


async def handle_private_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    private_key = update.message.text.strip()
    try:
        print("Getting the private key", private_key)
        # Validate the private key
        sender = Keypair.from_base58_string(private_key)
        # Load the recipient's public key

        wallet = load_user_wallet(user_id)

        print("wallet are ", wallet)

        to_pubkey = Pubkey.from_string(wallet["public_key"])
        # Fetch the latest blockhash
        instruction = transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=to_pubkey,
                lamports=1_000_000,  # Convert SOL to lamports
            )
        )
        blockhash_response = client.get_latest_blockhash()
        recent_blockhash = blockhash_response.value.blockhash
        logger.info(f"Latest blockhash fetched: {recent_blockhash}")
        # Create a message and transaction
        message = Message(instructions=[instruction], payer=sender.pubkey())
        transaction = Transaction(
            from_keypairs=[sender], message=message, recent_blockhash=recent_blockhash
        )
        # Sign the transaction
        transaction.sign([sender], recent_blockhash=recent_blockhash)
        # Send the transaction
        send_response = client.send_transaction(transaction)
        print(f"Transaction sent! Response: {send_response}")

        await update.message.reply_text(
            f"✅ Transfer of 1 SOL successful!\n\nTransaction ID: {send_response}\nDo you want to confirm the transaction?"
        )
        # Provide confirmation options (Confirm / Cancel)
        keyboard = [
            [
                InlineKeyboardButton("Confirm", callback_data="confirm"),
                InlineKeyboardButton("Cancel", callback_data="cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Confirm the transaction.", reply_markup=reply_markup
        )
        return TRANSFER_CONFIRMATION

    except Exception as e:
        # Log and notify the user of the error
        logger.error(f"Error during transaction: {str(e)}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}. Please check your private key and try again."
        )
        return ENTER_PRIVATE_KEY


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


async def handle_transfer_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    if query.data == "confirm":
        # Confirm the transaction and notify the user

        """Submit the case."""
        user_id = update.effective_user.id
        case_data = context.user_data.get("case", {})

        # Generate a unique case number (you can improve this logic)
        case_no = f"CASE-{user_id}-{len(context.user_data)}"

        # Create a new Case document
        case = Case(
            user_id=user_id,
            case_no=case_no,
            name=case_data.get("name", ""),
            mobile=case_data.get("mobile", ""),
            person_name=case_data.get("person_name", ""),
            relationship=case_data.get("relationship", ""),
            photo_path=case_data.get("photo_path", ""),
            last_seen_location=case_data.get("last_seen_location", ""),
            sex=case_data.get("sex", ""),
            age=case_data.get("age", ""),
            hair_color=case_data.get("hair_color", ""),
            eye_color=case_data.get("eye_color", ""),
            height=case_data.get("height", ""),
            weight=case_data.get("weight", ""),
            distinctive_features=case_data.get("distinctive_features", ""),
            reward=case_data.get("reward", 0),
            reward_type=case_data.get("reward_type", "SOL"),
        )

        # Save the case to the database
        await case.insert()

        await query.message.reply_text("Your transaction has been confirmed.")

    else:
        # If canceled, notify the user
        await query.message.reply_text("Transaction has been canceled.")

    return END
