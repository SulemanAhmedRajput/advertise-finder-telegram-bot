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
from handlers.listing_handler import ITEMS_PER_PAGE
from models.case_model import Case


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
    query = query.lower()
    return [p.name for p in get_provinces_for_country(country)]


async def fetch_cases_by_province(location):
    """
    Fetch cases from the database based on the province.
    """
    # Implement this function
    case = await Case.find({"last_seen_location": location}).to_list()
    return case


async def fetch_case_by_number(case_no):
    """
    Fetch a case from the database based on the case number.
    """
    # Implement this function
    case = await Case.find_one({"case_no": case_no})
    return case


async def choose_province(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    print("Hello from the choose province")
    user_id = update.effective_user.id
    txt = update.message.text.strip()
    # Replace this with the function to get matching provinces for the text input
    country = context.user_data.get("country", None)

    if not country:
        await update.message.reply_text(
            get_text(user_id, "country_not_found"), parse_mode="HTML"
        )
        return CHOOSE_COUNTRY

    matches = get_province_matches(txt, country)

    print(f"Matched Provinces are: {matches}")

    if len(matches) == 1:
        # If there's only one match, select it directly
        user_data_store[user_id]["province"] = matches[0]
        context.user_data["province"] = matches[0]
        # Proceed to next step (e.g., case creation or some other flow)
        await case_listing(update, context)  # Or whatever the next step is
        return CASE_LIST
    else:
        # If there are multiple matches, show the paginated list
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
    user_id = query.from_user.id

    if data.startswith("province_select_"):
        province = data.replace("province_select_", "")
        user_data_store[user_id]["province"] = province
        await query.edit_message_text(
            f"{get_text(user_id, 'province_selected')} {province}.",
            parse_mode="HTML",
        )
        # Proceed to the next step (case listing or whatever is next)
        return await case_listing(update, context)

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
    await query.answer() if query else None

    province = context.user_data.get("province")
    if not province:
        await update.effective_message.reply_text("Please select a province first.")
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
                "No cases found in this province."
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

        return CASE_LIST

    except Exception as e:
        logger.error(f"Error showing advertisements: {e}")
        await update.effective_message.reply_text(
            "Error loading cases. Please try again."
        )
        return END


async def case_details_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Show detailed information about a case"""
    print("case_details_callback")
    query = update.callback_query
    await query.answer()

    try:
        case_no = query.data.split("_")[1]
        case = await fetch_case_by_number(case_no)

        if not case:
            await query.edit_message_text("Case not found.")
            return END

        details = (
            f"🔍 Case #{case.case_no}\n\n"
            f"👤 Name: {case.person_name}\n"
            f"📍 Last Seen: {case.last_seen_location}\n"
            f"📅 Last Seen Date: {case.last_seen_date}\n"
            f"🏷️ Reward: {case.reward} {case.reward_currency}\n\n"
            f"ℹ️ Additional Info:\n{case.description}"
        )

        keyboard = [
            [
                InlineKeyboardButton(
                    "📌 Save Case", callback_data=f"save_{case.case_no}"
                )
            ],
            [
                InlineKeyboardButton(
                    "✅ Mark as Found", callback_data=f"found_{case.case_no}"
                )
            ],
            [InlineKeyboardButton("🔙 Back to List", callback_data="back_to_list")],
        ]

        await query.edit_message_text(
            details, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
        return CASE_DETAILS

    except Exception as e:
        logger.error(f"Error showing case details: {e}")
        await query.edit_message_text("Error loading case details.")
        return END


async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle uploaded proof with better file handling"""
    try:
        user_id = update.effective_user.id
        case_no = context.user_data.get("found_case_no")

        if not case_no:
            await update.message.reply_text(
                "Error: No case selected. Please start over."
            )
            return END

        # Create proofs directory if not exists
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
            await update.message.reply_text("❌ Please upload a photo or video.")
            return UPLOAD_PROOF

        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"proof_{user_id}_{case_no}_{timestamp}.{file_extension}"
        file_path = os.path.join("proofs", filename)

        # Download file
        file = await context.bot.get_file(file_id)
        await file.download_to_drive(file_path)

        # Store proof path in context
        context.user_data["proof_path"] = file_path

        await update.message.reply_text(
            "✅ Proof received. Please enter the location where you found this person:"
        )
        return ENTER_LOCATION

    except Exception as e:
        logger.error(f"Error handling proof: {e}")
        await update.message.reply_text(
            "❌ Error processing your proof. Please try again."
        )
        return UPLOAD_PROOF


async def notify_advertiser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Complete notification implementation"""
    try:
        location = update.message.text.strip()
        case_no = context.user_data.get("found_case_no")
        proof_path = context.user_data.get("proof_path")

        if not all([case_no, location, proof_path]):
            await update.message.reply_text(
                "❌ Missing information. Please start over."
            )
            return END

        # Fetch case details
        case = await fetch_case_by_number(case_no)
        if not case:
            await update.message.reply_text("❌ Case not found.")
            return END

        # Get advertiser's chat ID
        advertiser_chat_id = case.advertiser_id

        # Send notification to advertiser
        notification_text = (
            f"🚨 Potential Match Alert! 🚨\n\n"
            f"Case #{case.case_no}: {case.person_name}\n"
            f"📍 Reported Location: {location}\n"
            f"🔗 Proof File: {proof_path}"
        )

        await context.bot.send_message(
            chat_id=advertiser_chat_id, text=notification_text
        )

        # Confirm to finder
        await update.message.reply_text(
            "✅ The case owner has been notified!\n\n"
            "Thank you for your contribution. We'll contact you if more information is needed."
        )

        # Cleanup context
        context.user_data.pop("found_case_no", None)
        context.user_data.pop("proof_path", None)

        return END

    except Exception as e:
        logger.error(f"Error notifying advertiser: {e}")
        await update.message.reply_text(
            "❌ Error sending notification. Please try again later."
        )
        return END


async def handle_found_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle 'Found' button clicks from case details"""
    query = update.callback_query
    await query.answer()

    try:
        # Extract case number from callback data (format: found_<caseno>)
        case_no = query.data.split("_")[1]
        context.user_data["found_case_no"] = case_no

        # Ask for proof upload
        await query.edit_message_text("Please upload photo/video proof:")
        return UPLOAD_PROOF

    except Exception as e:
        logger.error(f"Error handling found case: {e}")
        await query.edit_message_text("Error processing request. Please try again.")
        return END
