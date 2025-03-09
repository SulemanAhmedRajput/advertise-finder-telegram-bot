from beanie import PydanticObjectId
from bson import ObjectId
import datetime
import os
import requests
import telegram

from telegram.ext import (
    ContextTypes,
)

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from config.config_manager import OWNER_TELEGRAM_ID
from constant.language_constant import ITEMS_PER_PAGE
from models.case_model import Case, CaseStatus
from handlers.listing_handler import logger
from models.extend_reward_model import ExtendReward, ExtendRewardStatus
from models.finder_model import FinderStatus, RewardExtensionStatus
from models.wallet_model import Wallet
from services.case_service import get_case_by_id
from services.wallet_service import WalletService
from utils.cloudinary import CloudinaryError, upload_image, upload_video
from utils.error_wrapper import catch_async
from utils.helper import paginate_list
from utils.wallet import load_user_wallet
from constants import State
from constant.language_constant import get_text, user_data_store
from services.finder_service import FinderService


def get_provinces_for_country(country):
    """
    Fetch provinces/states for the given country using REST Countries API.
    """
    print(f"Country: {country}")
    url = "https://countriesnow.space/api/v0.1/countries/states"
    data = {"country": country}

    response = requests.post(url, json=data)

    if response.status_code == 200:
        states = response.json()
        print(f"states: {states["data"]["states"]}")
        print([state["name"] for state in states["data"]["states"]])
        return [state["name"] for state in states["data"]["states"]]
    else:
        print("Failed to fetch states:", response.status_code)
        return []


def get_province_matches(query, country):
    """Geting the province match with query and inside the country which provided"""
    query = query.lower()
    provinces = get_provinces_for_country(country)
    return [province for province in provinces if query in province.lower()]


async def fetch_cases_by_province(location):
    """
    Fetch cases from the database based on the province.
    """
    # Implement this function
    case = await Case.find({"last_seen_location": location, "status": CaseStatus.ADVERTISE}).to_list()
    print(f"These are the cases for {location}: {case}")

    return case


async def fetch_case_by_number(case_no):
    """
    Fetch a case from the database based on the case number.
    """
    # Implement this function
    case = await Case.find_one({"_id": ObjectId(case_no)})
    return case


async def choose_province(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles province selection and shows cases for that province."""
    print("Hello from the choose province")
    user_id = update.effective_user.id
    txt = update.message.text.strip()

    # Get country from user_data
    country = context.user_data.get("country", None)
    city = context.user_data.get("city", None)

    if not country:
        await update.message.reply_text(
            get_text(user_id, "country_not_found"), parse_mode="HTML"
        )
        return State.CHOOSE_COUNTRY

    # Get matching provinces
    matches = get_province_matches(txt, country)
    print(f"Matched Provinces are: {matches}")

    if len(matches) == 1:
        # If there's only one match, fetch and display cases
        selected_province = matches[0]
        await FinderService.update_or_create_finder(
            user_id=user_id,
            province=selected_province,
            city=city,
            country=country,
        )
        context.user_data["province"] = selected_province  # Save province in context

        # Fetch cases from DB where last_seen_location matches province
        cases = await Case.find({"last_seen_location": selected_province, "status": CaseStatus.ADVERTISE}).to_list()

        if not cases:
            await update.message.reply_text(
                get_text(user_id, "no_case_found_in_province").format(
                    province=selected_province
                ),
                parse_mode="Markdown",
            )
            return State.CHOOSE_PROVINCE

        # Save case list in context for pagination
        context.user_data["cases"] = cases
        context.user_data["page"] = 1

        # Paginate cases
        paginated_cases, total_pages = paginate_list(cases, 1)

        # Create keyboard buttons for cases
        keyboard = [
            [
                InlineKeyboardButton(
                    f"Case {case.case_no} - {case.person_name}",
                    callback_data=f"case_{str(case.id)}",
                )
            ]
            for case in paginated_cases
        ]

        # Add pagination buttons
        navigation_buttons = []
        if total_pages > 1:
            navigation_buttons.append(
                InlineKeyboardButton("⬅️ Previous", callback_data="case_page_previous")
            )
            navigation_buttons.append(
                InlineKeyboardButton("➡️ Next", callback_data="case_page_next")
            )
        if navigation_buttons:
            keyboard.append(navigation_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📍 **Cases from {selected_province}:**",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return State.CASE_DETAILS  # Transition to case details handling

    else:
        # If multiple matches, show province selection UI
        user_data_store[user_id]["province_matches"] = matches
        user_data_store[user_id]["province_page"] = 1
        paginated, total = paginate_list(matches, 1)
        kb = []
        for p in paginated:
            kb.append([InlineKeyboardButton(p, callback_data=f"province_select_{p}")])

        # Pagination buttons
        if total > 1:
            kb.append(
                [
                    InlineKeyboardButton("⬅️", callback_data="province_page_0"),
                    InlineKeyboardButton("➡️", callback_data="province_page_2"),
                ]
            )
        markup = InlineKeyboardMarkup(kb)
        await update.message.reply_text(
            get_text(user_id, "province_multi").format(page=1, total=total),
            reply_markup=markup,
            parse_mode="HTML",
        )
        return State.CHOOSE_PROVINCE


# Function to handle the province selection callback
async def province_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith("province_select_"):
        province = data.replace("province_select_", "")
        context.user_data["province"] = province  # Save province in context
        await query.edit_message_text(
            f"{get_text(user_id, 'province_selected')} {province}.",
            parse_mode="HTML",
        )
        # Proceed to the next step (case listing or whatever is next)
        return await show_advertisements(update, context)

    elif data.startswith("province_page_"):
        # Handle pagination for provinces
        page_str = data.replace("province_page_", "")
        try:
            page_num = int(page_str)
            if page_num < 1:
                page_num = 1
        except ValueError:
            page_num = 1

        matches = user_data_store[user_id].get("province_matches", [])
        paginated, total = paginate_list(matches, page_num)
        kb = []
        for p in paginated:
            kb.append([InlineKeyboardButton(p, callback_data=f"province_select_{p}")])

        nav_row = []
        if page_num > 1:
            nav_row.append(
                InlineKeyboardButton("⬅️", callback_data=f"province_page_{page_num-1}")
            )
        if page_num < total:
            nav_row.append(
                InlineKeyboardButton("➡️", callback_data=f"province_page_{page_num+1}")
            )
        if nav_row:
            kb.append(nav_row)

        markup = InlineKeyboardMarkup(kb)
        await query.edit_message_text(
            get_text(user_id, "province_multi").format(page=page_num, total=total),
            reply_markup=markup,
            parse_mode="HTML",
        )

        user_data_store[user_id]["province_page"] = page_num
        return State.CHOOSE_PROVINCE

    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return State.END


# TODO: Why it has the seperate pagination function - Need to be fixe.


async def show_advertisements(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Show listings of advertisements with pagination"""
    print("\033show_advertisements\033[0m")
    query = update.callback_query
    user_id = update.effective_user.id

    await query.answer() if query else None

    province = context.user_data.get("province")
    if not province:
        await update.effective_message.reply_text(get_text(user_id, "select_province"))
        return State.CHOOSE_PROVINCE

    try:
        # Get current page from context
        page = context.user_data.get("page", 1)  # Default to page 1
        items_per_page = ITEMS_PER_PAGE

        # Fetch cases from database
        all_cases = await fetch_cases_by_province(province)
        total_cases = len(all_cases)

        if not all_cases:
            await update.effective_message.reply_text(
                get_text(user_id, "case_not_found_in_province")
            )
            return State.END

        # Pagination calculations
        total_pages = (total_cases + items_per_page - 1) // items_per_page
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        cases = all_cases[start_idx:end_idx]

        # Create case buttons
        keyboard = []
        for case in cases:
            case_info = f"Case #{case.case_no}: {case.person_name} ({case.age})"
            keyboard.append(
                [InlineKeyboardButton(case_info, callback_data=f"case_{case.id}")]
            )

        # Add pagination controls
        pagination_buttons = []
        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    "⬅️ Previous", callback_data=f"case_page_{page - 1}"
                )
            )
        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton("Next ➡️", callback_data=f"case_page_{page + 1}")
            )

        if pagination_buttons:
            keyboard.append(pagination_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"Cases in {province} (Page {page} of {total_pages}):"

        if query:
            await query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.effective_message.reply_text(text, reply_markup=reply_markup)

        return State.CASE_DETAILS

    except Exception as e:
        logger.error(f"Error showing advertisements: {e}")
        await update.effective_message.reply_text(
            get_text(user_id, "error_loading_cases")
        )
        return State.END


async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle pagination for case listings."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    # Extract page number from callback data
    if query.data.startswith("case_page_"):
        page_str = query.data.replace("case_page_", "")
        try:
            page = int(page_str)
            if page < 1:
                page = 1
        except ValueError:
            page = 1

        # Save updated page in context
        context.user_data["page"] = page

        # Re-fetch and display cases for the updated page
        return await show_advertisements(update, context)

    return State.CASE_DETAILS


async def case_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show detailed information about a case"""
    print("case_details_callback")
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    try:
        print(f"Printing the Query: {query.data}")
        case_id = query.data.split("_")[1]
        print(f"Case ID: {case_id}")
        await FinderService.update_or_create_finder(user_id, case=case_id)
        case = await fetch_case_by_number(case_id)

        if not case:
            await query.edit_message_text(get_text(user_id, "case_not_found"))
            return State.END

        wallet = await case.wallet.fetch() if case.wallet else None


        proof_text = (
            f"[Proof]({case.case_photo})"
            if case.case_photo and case.case_photo.startswith("http")
            else "No proof available"
        )
        

        details = (
            f"📌 **Case Details**\n"
            f"👤 **Person Name:** {case.person_name}\n"
            f"📍 **Last Seen Location:** {case.last_seen_location}\n"
            f"💰 **Reward:** {case.reward or 'None'} \n"
            f"👤 **Gender:** {case.gender}\n"
            f"🧒 **Age:** {case.age}\n"
            f"📏 **Height:** {case.height} cm\n"
        )
        
        details +=  f"\n\n**Proof:** {proof_text}"


        keyboard = [
            [
                InlineKeyboardButton(
                    get_text(user_id, "mark_as_found"),
                    callback_data=f"found_{case.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    get_text(user_id, "back_to_list"), callback_data="back_to_list"
                )
            ],
        ]

        # Send case details
        await query.message.reply_text(
            details, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

        return State.CASE_DETAILS

    except Exception as e:
        logger.error(f"Error showing case details: {e}")
        await query.edit_message_text(get_text(user_id, "error_loading_case"))
        return State.END


async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles uploaded proof (image or video) and uploads it to Cloudinary."""
    print("handle_proof")
    try:
        user_id = update.effective_user.id
        case_no = context.user_data.get("found_case_no")

        if not case_no:
            await update.message.reply_text(get_text(user_id, "no_case_selected"))
            return State.END

        # Ensure 'proofs' directory exists
        os.makedirs("proofs", exist_ok=True)

        file_id = None
        file_extension = None
        file_size = None
        is_video = False  # Flag to check if the file is a video

        # Check for photo or video
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            file_extension = "jpg"  # Telegram sends images in JPG format
        elif update.message.video:
            file_id = update.message.video.file_id
            file_extension = update.message.video.mime_type.split("/")[1]  # Get video format (e.g., mp4, mov, etc.)
            file_size = update.message.video.file_size  # File size in bytes
            is_video = True  # Mark this as a video upload
        else:
            await update.message.reply_text(get_text(user_id, "error_upload_proof"))
            return State.UPLOAD_PROOF

        # Define supported formats for both images and videos
        supported_image_formats = ["jpg", "jpeg", "png"]
        supported_video_formats = ["mp4", "mov", "avi", "mkv", "webm"]

        # Validate the file format
        if is_video:
            if file_extension not in supported_video_formats:
                await update.message.reply_text("Unsupported video format. Please upload a valid video (mp4, mov, avi, mkv, webm).")
                return State.UPLOAD_PROOF
            # Check video file size (5MB max)
            if file_size and file_size > 5 * 1024 * 1024:
                await update.message.reply_text("The file is too large. Please upload a video smaller than 5 MB.")
                return State.UPLOAD_PROOF
        else:
            if file_extension not in supported_image_formats:
                await update.message.reply_text("Unsupported image format. Please upload a valid image (jpg, jpeg, png).")
                return State.UPLOAD_PROOF

        # Generate unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"proof_{user_id}_{case_no}_{timestamp}.{file_extension}"
        file_path = os.path.join("proofs", filename)

        # Download file
        file = await context.bot.get_file(file_id)
        await file.download_to_drive(file_path)

        # Upload to Cloudinary
        try:
            if is_video:
                upload_result = await upload_video(file_path)
            else:
                upload_result = await upload_image(file_path)

            print(f"Uploaded File URL: {upload_result}")
        except CloudinaryError as e:
            print(f"Cloudinary upload error: {e}")
            await update.message.reply_text("There was an error uploading the file. Please try again.")
            return State.END

        await FinderService.update_or_create_finder(user_id, proof_url=[upload_result])

        # Store proof path in context
        context.user_data["proof_path"] = file_path

        await update.message.reply_text(get_text(user_id, "proof_received"))
        return State.ENTER_LOCATION

    except Exception as e:
        print(f"Error handling proof: {e}")
        await update.message.reply_text(get_text(user_id, "error_processing_proof"))
        return State.END


# TODO: Add a check to see if the user has already been notified
async def handle_enter_location(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Notify the advertiser and ask them to confirm the reward transfer."""
    user_id = update.effective_user.id
    try:
        location = update.message.text.strip()

        context.user_data["finder_location"] = location
        await FinderService.update_or_create_finder(user_id, reported_location=location)
        await update.message.reply_text(
            "Do you want to extend the reward?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("Yes", callback_data="yes_extend"),
                        InlineKeyboardButton("No", callback_data="no_extend"),
                    ],
                ]
            ),
        )
        return (
            State.EXTEND_REWARD
        )  # Ensure this matches the state name in your ConversationHandler

    except Exception as e:
        logger.error(f"Error notifying advertiser: {e}")
        await update.message.reply_text(get_text(user_id, "error_sending_notification"))
        return State.END

  



# ------------------------------------- FINDER  LOGIC  START ------------------------------------


@catch_async
async def finder_wallet_type_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Determine wallet type (SOL or USDT) from callback data
    wallet_type = query.data

    context.user_data["wallet_type"] = wallet_type

    print(f"Wallet type: {wallet_type}")

    existing_wallets = await WalletService.get_wallet_by_type(user_id, wallet_type)

    if existing_wallets:
        kb = [
            [
                InlineKeyboardButton(
                    wallet.name, callback_data=f"wallet_{str(wallet.id)}"
                )
            ]
            for wallet in existing_wallets
        ]
        kb.append(
            [
                InlineKeyboardButton(
                    get_text(user_id, "create_new_wallet"),
                    callback_data="create_new_wallet",
                )
            ]
        )
        await query.edit_message_text(
            get_text(user_id, "choose_existing_or_new_wallet"),
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode="HTML",
        )
        return State.FINDER_CHOOSE_WALLET_TYPE
    else:
        msg = get_text(user_id, "wallet_name_prompt")
        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.message.reply_text(msg, parse_mode="HTML")

        return State.FINDER_NAME_WALLET


@catch_async
async def finder_wallet_selection_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:

    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Extract wallet name and type from callback data
    wallet_id = query.data.replace("wallet_", "")
    wallet_type = context.user_data.get("wallet_type")  # 'sol' or 'usdt'

    case_id = context.user_data.get("found_case_no")
    case = await get_case_by_id(case_id)

    # Fetch wallet details by name and type
    wallet_details = await WalletService.get_wallet_by_id(wallet_id)

    print(f"Wallet details: {wallet_details}")

    if wallet_details:
        # Fetch balance for the specific wallet type (SOL or USDT)
        print(f"This is the wallet type: {wallet_type}")

        total_sol = (
            await WalletService.get_sol_balance(wallet_details["public_key"])
            if wallet_type == "SOL"
            else await WalletService.get_usdt_balance(wallet_details["public_key"])
        )

        print(f"Total {wallet_type}: {total_sol}")

        context.user_data["wallet"] = wallet_details  # Store in memory
        await FinderService.update_or_create_finder(
            user_id, wallet=str(wallet_details["id"])
        )

        msg = get_text(user_id, "wallet_create_details").format(
            name=wallet_details["name"],
            public_key=wallet_details["public_key"],
            secret_key=wallet_details["private_key"],
            balance=total_sol,  # For USDT, balance might be different
            wallet_type=wallet_type,
        )

        await query.edit_message_text(msg, parse_mode="HTML")

        # Show confirmation
        keyboard = [
            [
                InlineKeyboardButton(
                    "Confirm Transfer", callback_data="confirm_transfer"
                ),
                InlineKeyboardButton("Cancel", callback_data="cancel_transfer"),
            ]
        ]

        await query.edit_message_text(
            f"Are you Confirm you want the reward to {case.reward} {wallet_details["wallet_type"]} this Wallet ?\n"
            f"Wallet address: {wallet_details['public_key']}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return State.FINDER_CONFIRM_TRANSACTION

    else:
        await query.edit_message_text(
            get_text(user_id, "wallet_not_found"), parse_mode="HTML"
        )
        return State.END


@catch_async
async def finder_wallet_name_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    if update.callback_query:
        # If it's a callback query, prompt the user to enter a wallet name
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            get_text(user_id, "wallet_name_prompt"), parse_mode="HTML"
        )
        return State.NAME_WALLET

    wallet_name = update.message.text.strip()

    case_id = context.user_data.get("found_case_no")
    case = await get_case_by_id(case_id)

    print(f"Wallet name: {wallet_name}")

    if not wallet_name:
        await update.message.reply_text(
            get_text(user_id, "wallet_name_empty"), parse_mode="HTML"
        )
        return State.NAME_WALLET

    print("Hello there how are you doing", wallet_name)

    wallet_type = context.user_data.get("wallet_type")

    print(f"Wallet type: {wallet_type}")

    wallet = await WalletService.create_wallet(user_id, wallet_type, wallet_name)
    if wallet:

        if wallet_type == "SOL":
            total_sol = await WalletService.get_sol_balance(wallet.public_key)
        elif wallet_type == "USDT":
            total_sol = await WalletService.get_usdt_balance(wallet.public_key)

        print(f"Total SOL: {total_sol}")
        print(f"This is the wallet type: {wallet_type}")

        context.user_data["wallet"] = wallet
        msg = get_text(user_id, "wallet_create_details").format(
            name=wallet.name,
            public_key=wallet.public_key,
            secret_key=wallet.private_key,
            balance=total_sol,  # For USDT, the balance logic will vary
            wallet_type=wallet_type,
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "Confirm Transfer", callback_data="confirm_transfer"
                ),
                InlineKeyboardButton("Cancel", callback_data="cancel_transfer"),
            ]
        ]

        await query.edit_message_text(
            f"Confirm transfer of {case.reward} {wallet.wallet_type} from {wallet.name}?\n"
            f"Wallet address: {wallet.public_key}",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return State.FINDER_CONFIRM_TRANSACTION

    else:
        await update.message.reply_text(
            get_text(user_id, "wallet_create_err"), parse_mode="HTML"
        )
        return State.END
    
    


@catch_async
async def finder_handle_transaction_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    case_id = context.user_data.get("found_case_no")
    case = await get_case_by_id(PydanticObjectId(case_id))
    print("Case: ", case)
    wallet = await case.wallet.fetch(fetch_links=True)
    print(f"Wallet: {wallet}")
    print(f"Case: {case}")
    if case.status == CaseStatus.ADVERTISE:
        await FinderService.update_or_create_finder(user_id, case=case_id)
        # TODO: Add a check to see if the user has already been notified

        await context.bot.send_message(
            chat_id=case.user_id,
            text=f"🚨 Reward Extension Request 🚨\n\n"
            f"Finder is demanding {case.reward} {wallet.wallet_type}\n"
            f"Additional amount needed: {context.user_data['reward_difference']} {wallet.wallet_type}\n\n"
            f"Do you want to accept this extension?",
            # reply_markup=InlineKeyboardMarkup(keyboard),
        )
        await query.edit_message_text(
            f"Congratulate you finder request is send to the advertiser you will receive the reward when you accepted the request 🚀"
        )
        return State.END


# ------------------------------- FINDER LOGIC END ------------------------------------

#  ---------------------------- Extend Reward ---------------------------



async def handle_advertiser_response(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "reject_extend":
        await query.edit_message_text("Extension request rejected")
        return State.END

    # Get case details from context
    case_id = context.user_data.get("found_case_no")
    case = await Case.find_one({"_id": PydanticObjectId(case_id)}, fetch_links=True)

    # Get advertiser's wallets
    wallets = await WalletService.get_sol_wallet_of_user(case.user_id) \
        if case.wallet.wallet_type == "SOL" else \
        await WalletService.get_usdt_wallet_of_user(case.user_id)

    print(f"Wallets: {wallets}")

    if not wallets:
        # No wallets found, prompt to create one
        keyboard = [
            [
                InlineKeyboardButton(
                    "Create New Wallet", callback_data="create_extend_wallet"
                )
            ]
        ]
        await query.edit_message_text(
            "No wallets found. Please create a wallet to proceed:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return State.SELECT_WALLET

    # Show existing wallets
    keyboard = []
    for wallet in wallets:
        print(f"Wallet: {wallet}")
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{wallet.name}",
                    callback_data=f"select_extend_wallet_{wallet.id}",
                )
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                "Create New Wallet", callback_data="create_extend_wallet"
            )
        ]
    )

    await query.edit_message_text(
        "Select a wallet to use for the transfer:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return State.SELECT_WALLET


@catch_async
async def handle_transfer_confirmation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_transfer":
        await query.edit_message_text("Transfer cancelled")
        return State.END

    wallet = context.user_data["selected_wallet"]
    amount = context.user_data["reward_difference"]
    case_id = context.user_data.get("found_case_no")
    case = await get_case_by_id(PydanticObjectId(case_id))

    # Notify both parties
    await context.bot.send_message(
        chat_id=case.user_id,
        text=f"Successfully transferred {amount} {wallet.wallet_type}!\n"
        f"New total reward: {case.reward} {wallet.wallet_type}",
    )
    await context.bot.send_message(
        chat_id=context.user_data["finder_id"],  # Store finder ID earlier
        text=f"Reward extended to {case.reward} {wallet.wallet_type}!\n"
        f"The additional amount has been secured.",
    )
    await query.edit_message_text("Transfer successful! Reward updated.")


async def handle_confirm_found(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == "confirm_found":
        # Get case details
        case_id = context.user_data.get("found_case_no")
        case = await get_case_by_id(PydanticObjectId(case_id))
        await FinderService.update_or_create_finder(user_id, case=case_id)

        print(f"Inside the found case: {case}")

        if case:
            print(f"Inside the found case: {case}")
            reward_amount = case.reward  # Assuming reward is stored in case
            tax = reward_amount * 0.05
            final_reward = reward_amount - tax

            # Notify the advertiser (the one who posted the case)
            advertiser_message = (
                f"🔔 *Case Update*\n\n"
                f"Someone has confirmed finding the person in your case!\n\n"
                f"📌 *Case Details:*\n"
                f"👤 *Case ID:* {case_id}\n"
                f"💰 *Total Reward:* {reward_amount} SOL\n"
                f"⚖ *Tax (5%):* {tax:.2f} SOL\n"
                f"✅ *Final Payout:* {final_reward:.2f} SOL\n\n"
                f"🚀 The reward is being processed."
            )
            await context.bot.send_message(
                case.user_id, advertiser_message, parse_mode="Markdown"
            )

            # Notify the finder (who reported the found person)
            finder_message = (
                f"🎉 Congratulations! 🎉\n\n"
                f"The advertiser has been notified about your confirmation.\n"
                f"💰 Your estimated reward after tax: *{final_reward:.2f} SOL*\n\n"
                f"Please wait while the payment is processed. 🚀"
            )
            await context.bot.send_message(
                user_id, finder_message, parse_mode="Markdown"
            )

            # Notify the owner (admin/platform owner)
            owner_message = (
                f"🔔 *Admin Alert*\n\n"
                f"A case has been marked as *found*!\n\n"
                f"📌 *Case ID:* {case_id}\n"
                f"👤 *Advertiser:* {case.user_id}\n"
                f"🔎 *Finder:* {user_id}\n"
                f"💰 *Total Reward:* {reward_amount} SOL\n"
                f"⚖ *Tax (5%):* {tax:.2f} SOL\n"
                f"✅ *Final Payout:* {final_reward:.2f} SOL\n\n"
                f"📢 Please verify and ensure the reward is sent."
            )
            await context.bot.send_message(
                OWNER_TELEGRAM_ID, owner_message, parse_mode="Markdown"
            )

            await FinderService.update_or_create_finder(
                user_id,
                extended_reward_status=RewardExtensionStatus.PENDING,
                status=FinderStatus.FIND,
            )

            # Notify user in chat
            await query.message.reply_text(
                "The case owner and advertiser have been notified. Your reward will be sent soon! 💰"
            )
        else:
            await query.message.reply_text("Case not found. Please try again.")

        return State.END
    else:
        await query.message.reply_text("Okay, let us know if you have any updates.")
        return State.END


async def handle_found_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Found' button clicks from case details"""
    print(f"Inside the handle_found_case function")
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    try:
        # Extract case number from callback data (format: found_<caseno>)/
        case_no = query.data.split("_")[1]
        context.user_data["found_case_no"] = case_no

        # Ask for proof upload
        await query.edit_message_text(get_text(user_id, "proof_upload"))
        return State.UPLOAD_PROOF

    except Exception as e:
        logger.error(f"Error handling found case: {e}")
        await query.edit_message_text(get_text(user_id, "error_processing_proof"))
        return State.END




# ---------------------------- Extend Reward ---------------------------




@catch_async
async def handle_extend_reward_amount(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    print("I'm Inside the Handle Extend Reward Amount")

    user_id = update.effective_user.id
    new_reward_str = update.message.text.strip()
    context.user_data["extend_flow"] = True

    demanded_reward = float(new_reward_str)
    case_id = context.user_data.get("found_case_no")

    # Fetch the case with linked documents (wallet)
    case = await Case.find_one(
        {"_id": ObjectId(case_id)}, fetch_links=True  # Ensure wallet is fetched
    )
    # print(f"Case: {case}")

    print(f"Demand reward: {demanded_reward}")

   
   
    current_reward = float(case.reward )
    print(f"Current Reward: {current_reward}")
    
    if demanded_reward <= current_reward:
        await update.message.reply_text(
            f"Please enter an amount greater than current reward ({current_reward})"
        )
        return State.EXTEND_REWARD_AMOUNT

    context.user_data["demanded_reward"] = demanded_reward
    context.user_data["reward_difference"] = demanded_reward - current_reward

    extend_reward = ExtendReward(user_id=user_id, case=case, status=ExtendRewardStatus.PENDING,  extend_reward_amount=context.user_data['reward_difference'], reason="Just for the testing Purpose.")

    await extend_reward.save()

    # Notify advertiser
    await context.bot.send_message(
        chat_id=case.user_id,
        text=f"🚨 Reward Extension Request 🚨\n\n"
        f"Finder is demanding {demanded_reward} {case.wallet.wallet_type}\n"
        f"Additional amount needed: {context.user_data['reward_difference']} {case.wallet.wallet_type}\n\n"
        f"Do you want to accept this extension?",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Accept", callback_data="accept_extend"),
                    InlineKeyboardButton("Reject", callback_data="reject_extend"),
                ]
            ]
        ),
    )
    await update.message.reply_text("Extension request sent to case owner")
    return State.ADVERTISER_RESPONSE



#  ---------------------------- ADVERTISER LOGIC START ---------------------------



async def handle_extend_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    case_id = context.user_data.get("found_case_no")
    user_id = update.effective_user.id

    if query.data == "yes_extend":
        await query.message.reply_text("Please enter the new reward amount:")
        return State.EXTEND_REWARD_AMOUNT  # Transition to reward amount input
    else:
        # Handle "No" response
        case = await get_case_by_id(PydanticObjectId(case_id))

        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        get_text(user_id, "usdt_wallet"), callback_data="USDT"
                    ),
                    InlineKeyboardButton(
                        get_text(user_id, "sol_wallet"), callback_data="SOL"
                    ),
                ]
            ]
        )
        await query.edit_message_text(
            get_text(user_id, "choose_wallet"), reply_markup=kb
        )
        return State.FINDER_CHOOSE_WALLET_TYPE
    
    
    
    