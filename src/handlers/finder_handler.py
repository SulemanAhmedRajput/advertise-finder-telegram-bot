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
from constant.language_constant import ITEMS_PER_PAGE
from models.case_model import Case
from handlers.listing_handler import logger
from services.case_service import get_case_by_id
from services.wallet_service import WalletService
from utils.cloudinary import upload_image
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
    case = await Case.find({"last_seen_location": location}).to_list()
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
        cases = await Case.find({"last_seen_location": selected_province}).to_list()

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
        case = await fetch_case_by_number(case_id)

        if not case:
            await query.edit_message_text(get_text(user_id, "case_not_found"))
            return State.END

        wallet = await case.wallet.fetch() if case.wallet else None

        details = (
            f"📌 **Case Details**\n"
            f"👤 **Person Name:** {case.person_name}\n"
            f"📍 **Last Seen Location:** {case.last_seen_location}\n"
            f"💰 **Reward:** {case.reward or 'None'} \n"
            f"💼 **Wallet:** {wallet.public_key if wallet else 'Not provided'}\n"
            f"👤 **Gender:** {case.gender}\n"
            f"🧒 **Age:** {case.age}\n"
            f"📏 **Height:** {case.height} cm\n"
        )

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

        await query.edit_message_text(
            details, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
        return State.CASE_DETAILS

    except Exception as e:
        logger.error(f"Error showing case details: {e}")
        await query.edit_message_text(get_text(user_id, "error_loading_case"))
        return State.END


async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles uploaded proof and uploads it to Cloudinary."""
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

        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            file_extension = "jpg"
        elif update.message.video:
            file_id = update.message.video.file_id
            file_extension = "mp4"
        else:
            await update.message.reply_text(get_text(user_id, "error_upload_proof"))
            return State.UPLOAD_PROOF

        # Generate unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"proof_{user_id}_{case_no}_{timestamp}.{file_extension}"
        file_path = os.path.join("proofs", filename)

        # Download file
        file = await context.bot.get_file(file_id)
        await file.download_to_drive(file_path)

        # Upload the image to Cloudinary
        upload_result = await upload_image(
            file_path
        )  # Pass file path instead of File object
        if upload_result:
            print(f"Uploaded Image URL: {upload_result}")

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


async def handle_extend_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    case_id = context.user_data.get("found_case_no")

    if query.data == "yes_extend":
        await query.message.reply_text("Please enter the new reward amount:")
        return State.EXTEND_REWARD_AMOUNT  # Transition to reward amount input
    else:
        # Handle "No" response
        case = await get_case_by_id(PydanticObjectId(case_id))
        advertiser_id = case.user_id if case else None
        if advertiser_id:
            await context.bot.send_message(
                advertiser_id, "Someone has confirmed finding the person in your case!"
            )
        await query.message.reply_text(
            "Are you sure you have found this person?",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "Yes, Confirm", callback_data="confirm_found"
                        ),
                        InlineKeyboardButton(
                            "No, Cancel", callback_data="cancel_found"
                        ),
                    ],
                ]
            ),
        )
        return State.CONFIRM_FOUND


async def handle_extend_reward_amount(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    new_reward_str = update.message.text.strip()
    context.user_data["extend_flow"] = True

    try:
        demanded_reward = float(new_reward_str)
        case_id = context.user_data.get("found_case_no")
        case = await get_case_by_id(PydanticObjectId(case_id))

        if not case:
            await update.message.reply_text("Case not found")
            return State.END

        current_reward = case.reward or 0

        if demanded_reward <= current_reward:
            await update.message.reply_text(
                f"Please enter an amount greater than current reward ({current_reward})"
            )
            return State.EXTEND_REWARD_AMOUNT

        context.user_data["demanded_reward"] = demanded_reward
        context.user_data["reward_difference"] = demanded_reward - current_reward

        # Notify advertiser
        keyboard = [
            [
                InlineKeyboardButton("Accept", callback_data="accept_extend"),
                InlineKeyboardButton("Reject", callback_data="reject_extend"),
            ]
        ]

        wallet = await case.wallet.fetch()
        await context.bot.send_message(
            chat_id=case.user_id,
            text=f"🚨 Reward Extension Request 🚨\n\n"
            f"Finder is demanding {demanded_reward} {wallet.wallet_type}\n"
            f"Additional amount needed: {context.user_data['reward_difference']} {wallet.wallet_type}\n\n"
            f"Do you want to accept this extension?",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        await update.message.reply_text("Extension request sent to case owner")
        return State.ADVERTISER_RESPONSE

    except ValueError:
        await update.message.reply_text("Please enter a valid number")
        return State.EXTEND_REWARD_AMOUNT


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
    case = await get_case_by_id(PydanticObjectId(case_id))

    # Get advertiser's wallets
    wallets = await WalletService.get_wallet_by_user(user_id)

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
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{wallet.name} ({wallet.wallet_type})",
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


async def handle_wallet_selection(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "create_extend_wallet":
        await query.edit_message_text("Enter a name for your new wallet:")
        return State.NAME_WALLET

    wallet_id = query.data.split("_")[-1]
    wallet = await WalletService.get_wallet_by_id(wallet_id)

    if not wallet:
        await query.edit_message_text("Wallet not found")
        return State.END

    context.user_data["selected_wallet"] = wallet

    print(f"Wallet: {wallet}")

    # Check balance
    balance = (
        await WalletService.get_sol_balance(wallet.public_key)
        if wallet.wallet_type == "SOL"
        else await WalletService.get_usdt_balance(wallet.public_key)
    )
    required = context.user_data["reward_difference"]

    if balance < required:
        await query.edit_message_text(
            f"Insufficient balance. Needed: {required} {wallet.wallet_type}\n"
            f"Current balance: {balance} {wallet.wallet_type}"
        )
        return State.END

    # Show confirmation
    keyboard = [
        [
            InlineKeyboardButton("Confirm Transfer", callback_data="confirm_transfer"),
            InlineKeyboardButton("Cancel", callback_data="cancel_transfer"),
        ]
    ]

    await query.edit_message_text(
        f"Confirm transfer of {required} {wallet.wallet_type} from {wallet.name}?\n"
        f"Wallet address: {wallet.public_key}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return State.TRANSFER_CONFIRMATION


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

    try:
        # Perform actual transfer
        success = await WalletService.transfer(
            private_key=wallet.private_key,
            recipient_address=case.wallet.public_key,  # Assuming case has a wallet
            amount=amount,
            currency=wallet.type,
        )

        if success:
            # Update case reward
            case.reward = context.user_data["demanded_reward"]
            await case.save()

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
        else:
            await query.edit_message_text("Transfer failed. Please try again.")

    except Exception as e:
        logger.error(f"Transfer error: {e}")
        await query.edit_message_text("An error occurred during transfer")

    return State.END


async def handle_confirm_found(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_found":
        # Notify the owner
        case_id = context.user_data.get("found_case_no")
        case = await get_case_by_id(PydanticObjectId(case_id))
        if case:
            await context.bot.send_message(
                case.user_id, "Someone has confirmed finding the person in your case!"
            )
        await query.message.reply_text(
            "The case owner has been notified & reward would be sent to you soon."
        )
        return State.END
    else:
        query.message.reply_text("Okay, let us know if you have any updates.")
        return State.END


async def handle_found_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Found' button clicks from case details"""
    print(f"Inside the handle_found_case function")
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    try:
        # Extract case number from callback data (format: found_<caseno>)
        case_no = query.data.split("_")[1]
        context.user_data["found_case_no"] = case_no

        # Ask for proof upload
        await query.edit_message_text(get_text(user_id, "proof_upload"))
        return State.UPLOAD_PROOF

    except Exception as e:
        logger.error(f"Error handling found case: {e}")
        await query.edit_message_text(get_text(user_id, "error_processing_proof"))
        return State.END
