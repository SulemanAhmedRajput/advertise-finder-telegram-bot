from models.case_model import Case
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import logging
from bson import ObjectId  # Ensure ObjectId is imported
import traceback
import math
from constants import CASE_DETAILS, END

# Setup logging
logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 5  # Define how many cases to display per page


# Helper to paginate list items
def paginate_list(items, page, items_per_page=ITEMS_PER_PAGE):
    total_pages = max(1, math.ceil(len(items) / items_per_page)) if items else 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    end = start + items_per_page
    return items[start:end], total_pages


# Define states
async def listing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /listing command."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} issued /listing command")

    try:
        # Fetch all cases from the database
        cases = await Case.find().to_list()
        logger.info(f"Fetched {len(cases)} cases from the database")

        if not cases:
            await update.message.reply_text("No cases found in the database.")
            return END

        # Save the current page for pagination
        context.user_data["page"] = 1
        context.user_data["cases"] = cases

        # Paginate the case list
        paginated_cases, total_pages = paginate_list(cases, 1)

        # Create the inline keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    f"Case {case.case_no} - {case.person_name}",
                    callback_data=f"case_{str(case.id)}",  # Ensure prefix and convert ID to string
                )
            ]
            for case in paginated_cases
        ]

        # Add pagination buttons (previous/next)
        navigation_buttons = []
        if 1 < total_pages:
            navigation_buttons.append(
                InlineKeyboardButton("⬅️ Previous", callback_data="page_previous")
            )
        if 1 < total_pages:
            navigation_buttons.append(
                InlineKeyboardButton("➡️ Next", callback_data="page_next")
            )

        if navigation_buttons:
            keyboard.append(navigation_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the message with the case list
        await update.message.reply_text(
            "📋 **Select a Case to View Details:**",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return CASE_DETAILS

    except Exception as e:
        logger.error(f"Error in listing_command: {str(e)}\n{traceback.format_exc()}")
        await update.message.reply_text("An error occurred while fetching cases.")
        return END


async def case_details_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for displaying case details when a button is clicked."""
    query = update.callback_query
    await query.answer()

    try:
        case_id = query.data.removeprefix("case_")  # Extract case ID

        # Convert case_id to ObjectId before querying
        case = await Case.find_one({"_id": ObjectId(case_id)})
        if not case:
            await query.message.edit_text("❌ Case not found.")
            return END

        # Format the case details
        case_message = (
            f"📌 **Case Details**\n"
            f"🔹 **Case No:** {case.case_no}\n"
            f"👤 **Person Name:** {case.person_name}\n"
            f"📍 **Last Seen Location:** {case.last_seen_location}\n"
            f"💰 **Reward:** {case.reward} {case.reward_type}\n"
            f"📞 **Contact Info:** {case.mobile}\n"
        )

        # Edit the message to show case details
        await query.message.edit_text(case_message, parse_mode="Markdown")
        return END

    except Exception as e:
        logger.error(
            f"Error in case_details_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text(
            "❌ An error occurred while fetching case details."
        )
        return END


async def pagination_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for the pagination (Next/Previous) buttons."""
    query = update.callback_query
    await query.answer()

    # Get current page and case list from user data
    current_page = context.user_data.get("page", 1)
    cases = context.user_data.get("cases", [])

    # Determine navigation action (next or previous)
    if query.data == "page_next":
        new_page = current_page + 1
    elif query.data == "page_previous":
        new_page = current_page - 1
    else:
        new_page = current_page

    # Paginate the case list based on new page
    paginated_cases, total_pages = paginate_list(cases, new_page)

    # Save the new page in context
    context.user_data["page"] = new_page

    # Create the inline keyboard with case buttons
    keyboard = [
        [
            InlineKeyboardButton(
                f"Case {case.case_no} - {case.person_name}",
                callback_data=f"case_{str(case.id)}",
            )
        ]
        for case in paginated_cases
    ]

    # Add navigation buttons
    navigation_buttons = []
    if new_page > 1:
        navigation_buttons.append(
            InlineKeyboardButton("⬅️ Previous", callback_data="page_previous")
        )
    if new_page < total_pages:
        navigation_buttons.append(
            InlineKeyboardButton("➡️ Next", callback_data="page_next")
        )

    if navigation_buttons:
        keyboard.append(navigation_buttons)

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Edit the message with updated case list
    await query.message.edit_text(
        "📋 **Select a Case to View Details:**",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return CASE_DETAILS


# Define ConversationHandler
case_listing_handler = ConversationHandler(
    entry_points=[CommandHandler("listing", listing_command)],
    states={
        CASE_DETAILS: [
            CallbackQueryHandler(case_details_callback, pattern="^case_.*$"),
            CallbackQueryHandler(
                pagination_callback, pattern="^(page_previous|page_next)$"
            ),
        ]
    },
    fallbacks=[CommandHandler("cancel", lambda update, context: END)],
)
