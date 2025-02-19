from constant.language_constant import get_text, user_data_store
from models.case_model import Case
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
)
import logging

# Import your text-getting function and other constants
from constants import (
    State,
)
from services.case_service import update_or_create_case
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
        await update.message.reply_text(
            get_text(user_id, "choose_existing_mobile"),
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return State.MOBILE_MANAGEMENT
    else:
        # Ask for a new mobile number
        await update.message.reply_text(get_text(user_id, "enter_mobile"))
        return State.CREATE_CASE_MOBILE


async def handle_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's mobile number input."""
    user_id = update.effective_user.id
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
        # Ask for a new mobile number
        await update.message.reply_text(get_text(user_id, "enter_mobile"))
        return State.CREATE_CASE_MOBILE


async def handle_new_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the input of a new mobile number and send OTP."""
    user_id = update.effective_user.id
    mobile = update.message.text.strip()

    if not validate_mobile(mobile):
        await update.message.reply_text(get_text(user_id, "invalid_mobile_number"))
        return State.CREATE_CASE_MOBILE

    # Generate and send TAC (OTP)
    tac = generate_tac()  # Implement this function to generate a random TAC
    context.user_data["tac"] = tac
    context.user_data["mobile"] = mobile

    # Send TAC via Twilio (uncomment the following lines if Twilio is configured)
    # message = send_sms(mobile, tac)
    # if not message:  # Check if SMS was sent successfully
    #     await update.message.reply_text(get_text(user_id, "enter_mobile"))
    #     return CREATE_CASE_MOBILE

    print("Your TAC is " + tac)  # For debugging purposes

    await update.message.reply_text(get_text(user_id, "enter_tac"))
    return State.CREATE_CASE_TAC


async def handle_select_mobile(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the selection of an existing mobile number or adding a new one."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "mobile_add":
        # Ask for a new mobile number
        await query.edit_message_text(get_text(user_id, "enter_mobile"))
        return State.CREATE_CASE_MOBILE
    else:
        selected_mobile = query.data.replace("select_mobile_", "")

        tac = generate_tac()  # Implement this function to generate a random TAC
        context.user_data["tac"] = tac
        context.user_data["mobile"] = selected_mobile
        await query.edit_message_text(
            f"Selected mobile number: {selected_mobile} - A TAC IS SEND TO YOU ON THIS NUMBER"
        )

        # Proceed to the next step in the case creation flow
        await query.message.reply_text(get_text(user_id, "enter_tac"))
        return State.CREATE_CASE_TAC


async def handle_tac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle TAC verification."""
    user_id = update.effective_user.id
    user_tac = update.message.text.strip()
    stored_tac = context.user_data.get("tac")

    print(f"Getting the number which are: {context.user_data.get("mobile")}")

    if user_tac == stored_tac:
        # if user_tac == "123456":
        await update.message.reply_text(get_text(user_id, "tac_verified"))
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
        return State.CREATE_CASE_REWARD_TYPE
    else:
        await query.edit_message_text(get_text(user_id, "disagree_end"))
        return State.END


# First handler to ask for the type (Solana or BTC)
async def handle_reward_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    logger.info(f"Reward type selected: {query.data}")  # Debugging line
    if query.data == "SOL":
        await update_or_create_case(user_id, reward_type=query.data)
        await query.edit_message_text(
            get_text(user_id, "enter_reward_amount"), parse_mode="HTML"
        )
        return State.CREATE_CASE_REWARD_AMOUNT
    elif query.data == "USDT":
        await query.edit_message_text(get_text(user_id, "btc_dev"), parse_mode="HTML")
        return State.END
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return State.END


# Handler for reward amount
async def handle_reward_amount(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    try:
        reward = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid amount, please enter a valid number.")
        return State.CREATE_CASE_REWARD_AMOUNT

    await update_or_create_case(user_id, reward=reward)
    context.user_data["case"]["reward"] = reward

    await update.message.reply_text("Please enter the person's name.")
    return State.CREATE_CASE_PERSON_NAME


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
    # await update.message.reply_text(get_text(user_id, "send_photo"))

    await update.message.reply_text(get_text(user_id, "upload_photo"))
    return State.CREATE_CASE_PHOTO
    # return CREATE_CASE_LAST_SEEN_LOCATION


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
    return State.ENTER_PRIVATE_KEY


async def handle_private_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Check sender's balance, store transaction details, and ask for confirmation."""
    user_id = update.effective_user.id
    private_key = update.message.text.strip()

    try:
        print("Getting the private key", private_key)
        # Validate the private key
        sender = Keypair.from_base58_string(private_key)

        # Fetch sender's balance
        sender_balance_response = client.get_balance(sender.pubkey())
        sender_balance = (
            sender_balance_response.value / 1e9
        )  # Convert from lamports to SOL
        logger.info(f"Sender balance: {sender_balance} SOL")

        # Load the recipient's public key
        wallet = load_user_wallet(user_id)
        print("wallet are ", wallet)

        to_pubkey = Pubkey.from_string(wallet["public_key"])
        total_sol = context.user_data["case"]["reward"]

        # Check if sender has enough balance
        if sender_balance < total_sol:
            await update.message.reply_text(
                f"❌ Insufficient funds. You have {sender_balance:.5f} SOL, but need {total_sol:.5f} SOL."
            )
            return (
                State.ENTER_PRIVATE_KEY
            )  # Ask user to re-enter key or handle accordingly

        # Fetch the latest blockhash
        blockhash_response = client.get_latest_blockhash()
        recent_blockhash = blockhash_response.value.blockhash
        logger.info(f"Latest blockhash fetched: {recent_blockhash}")

        print(f"Transaction Lamport: {int(total_sol * 1e9)}")

        # Create a transfer instruction
        instruction = transfer(
            TransferParams(
                from_pubkey=sender.pubkey(),
                to_pubkey=to_pubkey,
                lamports=int(total_sol * 1e9),  # Convert SOL to lamports
            )
        )

        # Create a message and transaction
        message = Message(instructions=[instruction], payer=sender.pubkey())
        transaction = Transaction(
            from_keypairs=[sender], message=message, recent_blockhash=recent_blockhash
        )

        # Store transaction details temporarily in context (DO NOT execute yet)
        context.user_data["transaction"] = {
            "private_key": private_key,  # Keep private key for signing later
            "transaction": transaction,  # Store transaction object
            "recent_blockhash": recent_blockhash,
        }

        # Ask the user to confirm the transaction
        keyboard = [
            [
                InlineKeyboardButton("Confirm", callback_data="confirm"),
                InlineKeyboardButton("Cancel", callback_data="cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ Transfer of {total_sol} SOL is ready.\n\n"
            "Do you want to confirm the transaction?",
            reply_markup=reply_markup,
        )

        return State.TRANSFER_CONFIRMATION

    except Exception as e:
        logger.error(f"Error during transaction preparation: {str(e)}")
        await update.message.reply_text(
            f"❌ Error: {str(e)}. Please check your private key and try again."
        )
        return State.ENTER_PRIVATE_KEY


async def handle_transfer_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Execute the transaction if the user confirms, otherwise cancel."""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm":
        try:
            # Retrieve stored transaction details
            transaction_data = context.user_data.get("transaction")
            if not transaction_data:
                await query.message.reply_text("❌ Error: No transaction found.")
                return State.END

            private_key = transaction_data["private_key"]
            transaction = transaction_data["transaction"]
            recent_blockhash = transaction_data["recent_blockhash"]

            # Recreate the sender keypair
            sender = Keypair.from_base58_string(private_key)

            # Sign and send the transaction
            transaction.sign([sender], recent_blockhash=recent_blockhash)
            send_response = client.send_transaction(transaction)
            logger.info(f"Transaction sent! Response: {send_response}")

            await query.message.reply_text(
                f"✅ Transfer successful!\n\nTransaction ID: {send_response}"
            )

            """Submit the case."""
            user_id = query.from_user.id
            case_data = context.user_data.get("case", {})

            # Generate a unique case number
            case_no = f"CASE-{user_id}-{len(context.user_data)}"

            # Create and insert case into the database
            case = Case(
                user_id=user_id,
                case_no=case_no,
                name=case_data.get("name", ""),
                mobile=context.user_data.get("mobile"),
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
            await case.insert()

            wallet = Wallet(
                public_key=user_data_store[user_id]["wallet"]["public_key"],
                private_key=user_data_store[user_id]["wallet"]["secret_key"],
                case_no=case_no,
                user_id=user_id,
            )

            await wallet.insert()

            await query.message.reply_text("✅ Your transaction has been confirmed.")

        except Exception as e:
            logger.error(f"Error executing transaction: {str(e)}")
            await query.message.reply_text(
                f"❌ Transaction failed: {str(e)}. Please try again."
            )

    else:
        # If canceled, notify the user
        await query.message.reply_text("❌ Transaction has been canceled.")

    return State.END
