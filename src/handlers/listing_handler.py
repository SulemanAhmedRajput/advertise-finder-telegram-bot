from models.case_model import Case, CaseStatus
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
from utils.helper import paginate_list


# Setup logging
logger = logging.getLogger(__name__)


async def listing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /listing command."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} issued /listing command")
    try:
        # Fetch all ADVERTISE cases from the database
        all_cases = await Case.find({"status": CaseStatus.ADVERTISE}).to_list()

        logger.info(f"Fetched {len(all_cases)} ADVERTISE cases from the database")
        if not all_cases:
            await update.message.reply_text("No ADVERTISE cases found.")
            return END

        # Save the current page for pagination
        context.user_data["page"] = 1
        context.user_data["cases"] = all_cases

        # Paginate the case list
        paginated_cases, total_pages = paginate_list(all_cases, 1)

        # Create the inline keyboard
        keyboard = []
        for case in paginated_cases:
            row = [
                InlineKeyboardButton(
                    f"Case {case.case_no} - {case.person_name}",
                    callback_data=f"case_{str(case.id)}",
                )
            ]
            # Add an "Edit" button if the user owns the case
            if case.user_id == user_id:
                row.append(
                    InlineKeyboardButton(
                        "📝 Edit", callback_data=f"edit_{str(case.id)}"
                    )
                )
            keyboard.append(row)

        # Add pagination buttons (previous/next)
        navigation_buttons = []
        current_page = context.user_data["page"]
        if current_page > 1:
            navigation_buttons.append(
                InlineKeyboardButton("⬅️ Previous", callback_data="page_previous")
            )
        if current_page < total_pages:
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

        # Add an "Edit" button if the user owns the case
        user_id = update.effective_user.id
        keyboard = []
        if case.user_id == user_id:
            keyboard.append(
                [InlineKeyboardButton("📝 Edit", callback_data=f"edit_{str(case.id)}")]
            )
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        # Edit the message to show case details
        await query.message.edit_text(
            case_message,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return END
    except Exception as e:
        logger.error(
            f"Error in case_details_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text(
            "❌ An error occurred while fetching case details."
        )
        return END


async def edit_case_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for editing a case."""
    query = update.callback_query
    await query.answer()
    try:
        case_id = query.data.removeprefix("edit_")  # Extract case ID
        # Convert case_id to ObjectId before querying
        case = await Case.find_one({"_id": ObjectId(case_id)})
        if not case:
            await query.message.edit_text("❌ Case not found.")
            return END

        # Check if the user owns the case
        user_id = update.effective_user.id
        if case.user_id != user_id:
            await query.message.edit_text(
                "❌ You are not authorized to edit this case."
            )
            return END

        # Provide options to edit the case (e.g., name, reward, etc.)
        keyboard = [
            [InlineKeyboardButton("Edit Name", callback_data=f"edit_name_{case_id}")],
            [
                InlineKeyboardButton(
                    "Edit Reward", callback_data=f"edit_reward_{case_id}"
                )
            ],
            [InlineKeyboardButton("Cancel", callback_data="cancel_edit")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.message.edit_text(
            "📝 **What would you like to edit?**",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return CASE_DETAILS
    except Exception as e:
        logger.error(f"Error in edit_case_callback: {str(e)}\n{traceback.format_exc()}")
        await query.message.edit_text("❌ An error occurred while editing the case.")
        return END


async def edit_name_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for editing the name of a case."""
    query = update.callback_query
    await query.answer()
    try:
        case_id = query.data.removeprefix("edit_name_")  # Extract case ID
        case = await Case.find_one({"_id": ObjectId(case_id)})
        if not case:
            await query.message.edit_text("❌ Case not found.")
            return END

        # Check if the user owns the case
        user_id = update.effective_user.id
        if case.user_id != user_id:
            await query.message.edit_text(
                "❌ You are not authorized to edit this case."
            )
            return END

        # Prompt the user to enter a new name
        await query.message.edit_text("📝 Please enter the new name for the case:")
        context.user_data["edit_case_id"] = case_id
        context.user_data["edit_field"] = "name"
        return CASE_DETAILS
    except Exception as e:
        logger.error(f"Error in edit_name_callback: {str(e)}\n{traceback.format_exc()}")
        await query.message.edit_text("❌ An error occurred while editing the case.")
        return END


async def edit_reward_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for editing the reward of a case."""
    query = update.callback_query
    await query.answer()
    try:
        case_id = query.data.removeprefix("edit_reward_")  # Extract case ID
        case = await Case.find_one({"_id": ObjectId(case_id)})
        if not case:
            await query.message.edit_text("❌ Case not found.")
            return END

        # Check if the user owns the case
        user_id = update.effective_user.id
        if case.user_id != user_id:
            await query.message.edit_text(
                "❌ You are not authorized to edit this case."
            )
            return END

        # Prompt the user to enter a new reward
        await query.message.edit_text(
            "📝 Please enter the new reward amount for the case:"
        )
        context.user_data["edit_case_id"] = case_id
        context.user_data["edit_field"] = "reward"
        return CASE_DETAILS
    except Exception as e:
        logger.error(
            f"Error in edit_reward_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text("❌ An error occurred while editing the case.")
        return END


async def edit_reward_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for editing the reward of a case."""
    query = update.callback_query
    await query.answer()
    try:
        case_id = query.data.removeprefix("edit_reward_")  # Extract case ID
        case = await Case.find_one({"_id": ObjectId(case_id)})
        if not case:
            await query.message.edit_text("❌ Case not found.")
            return END

        # Check if the user owns the case
        user_id = update.effective_user.id
        if case.user_id != user_id:
            await query.message.edit_text(
                "❌ You are not authorized to edit this case."
            )
            return END

        # Prompt the user to enter a new reward
        await query.message.edit_text(
            "📝 Please enter the new reward amount for the case:"
        )
        context.user_data["edit_case_id"] = case_id
        context.user_data["edit_field"] = "reward"
        return CASE_DETAILS
    except Exception as e:
        logger.error(
            f"Error in edit_reward_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text("❌ An error occurred while editing the case.")
        return END


async def pagination_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for the pagination (Next/Previous) buttons."""
    query = update.callback_query
    await query.answer()

    try:
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

        # Paginate the case list based on the new page
        paginated_cases, total_pages = paginate_list(cases, new_page)

        # Save the new page in context
        context.user_data["page"] = new_page

        # Create the inline keyboard with case buttons
        keyboard = []
        for case in paginated_cases:
            row = [
                InlineKeyboardButton(
                    f"Case {case.case_no} - {case.person_name}",
                    callback_data=f"case_{str(case.id)}",
                )
            ]
            # Add an "Edit" button if the user owns the case
            user_id = update.effective_user.id
            if case.user_id == user_id:
                row.append(
                    InlineKeyboardButton(
                        "📝 Edit", callback_data=f"edit_{str(case.id)}"
                    )
                )
            keyboard.append(row)

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

        # Edit the message with the updated case list
        await query.message.edit_text(
            "📋 **Select a Case to View Details:**",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return CASE_DETAILS
    except Exception as e:
        logger.error(
            f"Error in pagination_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text("❌ An error occurred while paginating cases.")
        return END


async def cancel_edit_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for canceling the edit process."""
    query = update.callback_query
    await query.answer()
    try:
        # Clear any edit-related data from context
        context.user_data.pop("edit_case_id", None)
        context.user_data.pop("edit_field", None)

        # Return to the case listing
        await query.message.edit_text("📋 Edit canceled. Returning to case listing.")
        return END
    except Exception as e:
        logger.error(
            f"Error in cancel_edit_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text("❌ An error occurred while canceling the edit.")
        return END
