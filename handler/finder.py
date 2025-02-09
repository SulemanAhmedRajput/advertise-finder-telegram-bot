import requests
from constants import (
    CASE_DETAILS,
    CASE_LIST,
    CHOOSE_COUNTRY,
    CHOOSE_PROVINCE,
    END,
    ENTER_LOCATION,
    UPLOAD_PROOF,
)
import telegram

from telegram.ext import (
    ContextTypes,
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from handler.listing import ITEMS_PER_PAGE
from src.models.case_model import Case


def get_provinces_for_country(country):
    """
    Fetch provinces/states for the given country using REST Countries API.
    """
    response = requests.get(f"https://restcountries.com/v3.1/name/{country}")
    if response.status_code == 200:
        data = response.json()
        # Extract states/provinces if available
        if data and "subdivisions" in data[0]:
            return data[0]["subdivisions"]
    return []


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
    """List provinces/cities in the selected country."""

    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()
    country = context.user_data["country"]

    if not country:
        await query.edit_message_text(
            "Please select a country first.", parse_mode="HTML"
        )
        return CHOOSE_COUNTRY

    # Fetch provinces/cities based on the selected country
    provinces = get_provinces_for_country(country)  # Implement this function

    keyboard = []
    for i, province in enumerate(provinces):
        if i % 2 == 0:
            keyboard.append([])  # Start a new row
        keyboard[-1].append(
            InlineKeyboardButton(province, callback_data=f"province_{province}")
        )

    # Add "More" button if the list is long
    if len(provinces) > ITEMS_PER_PAGE:
        keyboard.append([InlineKeyboardButton("More", callback_data="more_provinces")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"Select a province in {country}:", reply_markup=reply_markup
    )
    return CHOOSE_PROVINCE


# async def show_advertisements(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Show listings of advertisements."""
#     user_id = update.effective_user.id
#     query = update.callback_query
#     await query.answer()

#     # Fetch cases from the database
#     cases = fetch_cases_by_province(
#         context.user_data.get("province")
#     )  # Implement this function

#     keyboard = []
#     for case in cases:
#         case_info = f"{case['case_no']} | {case['name']} | {case['last_seen']} | 📷 | {case['reward']} SOL"
#         keyboard.append(
#             [InlineKeyboardButton(case_info, callback_data=f"case_{case['case_no']}")]
#         )

#     # Add pagination buttons if needed
#     if len(cases) > ITEMS_PER_PAGE:
#         keyboard.append(
#             [
#                 InlineKeyboardButton("Previous", callback_data="page_previous"),
#                 InlineKeyboardButton("Next", callback_data="page_next"),
#             ]
#         )

#     reply_markup = InlineKeyboardMarkup(keyboard)
#     await query.edit_message_text("Available cases:", reply_markup=reply_markup)
#     return CASE_LIST


# async def case_details_callback(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Show detailed information about a case."""
#     query = update.callback_query
#     await query.answer()
#     user_id = query.from_user.id

#     # Extract case number from callback data
#     case_no = query.data.split("_")[1]
#     case = fetch_case_by_number(case_no)  # Implement this function

#     # Build detailed message
#     details = (
#         f"Name: {case['person_name']}\n"
#         f"Last Seen: {case['last_seen_location']}\n"
#         f"Photos: [View Photo]({case['photo_path']})\n"
#         f"Reward: {case['reward']} SOL\n"
#     )

#     # Add buttons for "Save" and "Found"
#     keyboard = [
#         [InlineKeyboardButton("Save", callback_data=f"save_{case_no}")],
#         [InlineKeyboardButton("Found", callback_data=f"found_{case_no}")],
#     ]
#     reply_markup = InlineKeyboardMarkup(keyboard)

#     await query.edit_message_text(
#         details, reply_markup=reply_markup, parse_mode="Markdown"
#     )
#     return CASE_DETAILS


# async def handle_found_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Handle submission of a found case."""
#     query = update.callback_query
#     await query.answer()
#     user_id = query.from_user.id

#     # Extract case number from callback data
#     case_no = query.data.split("_")[1]
#     context.user_data["found_case_no"] = case_no

#     # Ask for proof (photo/video)
#     await query.message.reply_text("Please upload a photo or video as proof.")
#     return UPLOAD_PROOF


# async def handle_proof(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Handle uploaded proof."""
#     user_id = update.effective_user.id
#     case_no = context.user_data.get("found_case_no")

#     # Check if the user sent a photo or video
#     if update.message.photo:
#         proof_file = await update.message.photo[-1].get_file()
#         proof_path = f"proofs/{user_id}_{case_no}_proof.jpg"
#         await proof_file.download_to_drive(proof_path)
#         context.user_data["proof_path"] = proof_path
#     elif update.message.video:
#         proof_file = await update.message.video.get_file()
#         proof_path = f"proofs/{user_id}_{case_no}_proof.mp4"
#         await proof_file.download_to_drive(proof_path)
#         context.user_data["proof_path"] = proof_path
#     else:
#         await update.message.reply_text(
#             "Invalid proof. Please upload a photo or video."
#         )
#         return UPLOAD_PROOF

#     # Ask for the location where the person was found
#     await update.message.reply_text("Enter the location where the person was found:")
#     return ENTER_LOCATION


# async def notify_advertiser(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
#     """Notify the advertiser about the found case."""
#     pass
#     # user_id = update.effective_user.id
#     # case_no = context.user_data.get("found_case_no")
#     # location = update.message.text.strip()

#     # # Fetch advertiser's chat ID
#     # advertiser_chat_id = fetch_advertiser_chat_id(case_no)  # Implement this function

#     # # Send notification to the advertiser
#     # await context.bot.send_message(
#     #     chat_id=advertiser_chat_id,
#     #     text=f"Someone has found the person in your case #{case_no}. Location: {location}",
#     # )

#     # # Confirm to the finder
#     # await update.message.reply_text("The advertiser has been notified. Thank you!")
#     # return END
