from bson import ObjectId
import datetime
import os
import requests
from constants import (
    CASE_DETAILS,
    CASE_LIST,
    CHOOSE_COUNTRY,
    CHOOSE_PROVINCE,
    END,
    ENTER_LOCATION,
    UPLOAD_PROOF,
    get_text,
    CASE_LIST,
    user_data_store,
)
import telegram

from telegram.ext import (
    ContextTypes,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from handlers.listing_handler import ITEMS_PER_PAGE, paginate_list
from models.case_model import Case
from handlers.listing_handler import logger
from utils.cloudinary import upload_image


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

    if not country:
        await update.message.reply_text(
            get_text(user_id, "country_not_found"), parse_mode="HTML"
        )
        return CHOOSE_COUNTRY

    # Get matching provinces
    matches = get_province_matches(txt, country)
    print(f"Matched Provinces are: {matches}")

    if len(matches) == 1:
        # If there's only one match, fetch and display cases
        selected_province = matches[0]
        context.user_data["province"] = selected_province

        # Fetch cases from DB where last_seen_location matches province
        cases = await Case.find({"last_seen_location": selected_province}).to_list()

        if not cases:
            await update.message.reply_text(
                get_text(user_id, "no_case_found_in_province").format(
                    province=selected_province
                ),
                parse_mode="Markdown",
            )
            return CHOOSE_PROVINCE

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
        return CASE_DETAILS  # Transition to case details handling

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
        return CHOOSE_PROVINCE


# Function to handle the province selection callback
async def province_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    if data.startswith("province_select_"):
        province = data.replace("province_select_", "")
        user_data_store[user_id]["province"] = province
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
        return CHOOSE_PROVINCE

    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return END


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
        return CHOOSE_PROVINCE

    try:
        # Get current page and calculate offset
        page = context.user_data.get("page", 0)
        items_per_page = ITEMS_PER_PAGE

        # Fetch cases from database
        all_cases = await fetch_cases_by_province(province)
        total_cases = len(all_cases)

        if not all_cases:
            await update.effective_message.reply_text(
                get_text(user_id, "case_not_found_in_province")
            )
            return END

        # Pagination calculations
        total_pages = (total_cases + items_per_page - 1) // items_per_page
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        cases = all_cases[start_idx:end_idx]

        # Create case buttons
        keyboard = []
        for case in cases:
            case_info = f"Case #{case.case_no}: {case.person_name} ({case.age})"
            keyboard.append(
                [InlineKeyboardButton(case_info, callback_data=f"case_{case.case_no}")]
            )

        # Add pagination controls
        pagination_buttons = []
        if page > 0:
            pagination_buttons.append(
                InlineKeyboardButton("⬅ Previous", callback_data="page_previous")
            )
        if page < total_pages - 1:
            pagination_buttons.append(
                InlineKeyboardButton("Next ➡", callback_data="page_next")
            )

        if pagination_buttons:
            keyboard.append(pagination_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"Cases in {province} (Page {page+1} of {total_pages}):"

        if query:
            await query.edit_message_text(text, reply_markup=reply_markup)
        else:
            await update.effective_message.reply_text(text, reply_markup=reply_markup)

        return CASE_DETAILS

    except Exception as e:
        logger.error(f"Error showing advertisements: {e}")
        await update.effective_message.reply_text(
            get_text(user_id, "error_loading_cases")
        )
        return END


async def case_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show detailed information about a case"""
    print("case_details_callback")
    query = update.callback_query
    user_id = update.effective_user.id
    await query.answer()

    try:
        print(f"Printing the Query: {query.data}")
        case_no = query.data.split("_")[1]
        print(f"Case Number are {case_no}")
        case = await fetch_case_by_number(case_no)

        if not case:
            await query.edit_message_text(get_text(user_id, "case_not_found"))
            return END

        details = (
            f"🔍 Case #{case.case_no}\n\n"
            f"👤 Name: {case.person_name}\n"
            f"📍 Last Seen: {case.last_seen_location}\n"
            # f"📅 Last Seen Date: {case.last_seen_date}\n"
            # f"🏷️ Reward: {case.reward} {case.reward_currency}\n\n"
            # f"ℹ️ Additional Info:\n{case.description}"
        )

        keyboard = [
            # [
            #     InlineKeyboardButton(
            #         "📌 Save Case", callback_data=f"save_{case.case_no}"
            #     )
            # ],
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
        return CASE_DETAILS

    except Exception as e:
        logger.error(f"Error showing case details: {e}")
        await query.edit_message_text(get_text(user_id, "error_loading_case"))
        return END


async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles uploaded proof and uploads it to Cloudinary."""
    print("handle_proof")
    try:
        user_id = update.effective_user.id
        case_no = context.user_data.get("found_case_no")

        if not case_no:
            await update.message.reply_text(get_text(user_id, "no_case_selected"))
            return END

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
            return UPLOAD_PROOF

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
        return ENTER_LOCATION

    except Exception as e:
        print(f"Error handling proof: {e}")
        await update.message.reply_text(get_text(user_id, "error_processing_proof"))
        return UPLOAD_PROOF


# TODO: Add a check to see if the user has already been notified
async def notify_advertiser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Complete notification implementation"""
    user_id = update.effective_user.id
    try:
        location = update.message.text.strip()
        case_no = context.user_data.get("found_case_no")
        proof_path = context.user_data.get("proof_path")

        if not all([case_no, location, proof_path]):
            await update.message.reply_text(get_text(user_id, "missing_information"))
            return END

        # Fetch case details
        case = await fetch_case_by_number(case_no)
        if not case:
            await update.message.reply_text(get_text(user_id, "case_not_found"))
            return END

        # Get advertiser's chat ID
        advertiser_chat_id = case.user_id

        # Send notification to advertiser
        notification_text = get_text(user_id, "notification_text").format(
            case_no=case.case_no,
            person_name=case.person_name,
            location=location,
            proof_path="Dev Mode",
        )

        await context.bot.send_message(
            chat_id=advertiser_chat_id, text=notification_text
        )

        # Confirm to finder
        await update.message.reply_text(get_text(user_id, "reply_to_advertiser"))

        # Cleanup context
        context.user_data.pop("found_case_no", None)
        context.user_data.pop("proof_path", None)

        return END

    except Exception as e:
        logger.error(f"Error notifying advertiser: {e}")
        await update.message.reply_text(get_text(user_id, "error_sending_notification"))
        return END


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
        return UPLOAD_PROOF

    except Exception as e:
        logger.error(f"Error handling found case: {e}")
        await query.edit_message_text(get_text(user_id, "error_processing_proof"))
        return END
