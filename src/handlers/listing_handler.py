import logging
from datetime import datetime
from beanie import PydanticObjectId
from constants import State
from models.case_model import Case, CaseStatus
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from bson import ObjectId, errors
import traceback
import math
from utils.helper import paginate_list

# Setup logging
logger = logging.getLogger(__name__)


# Handlers
async def listing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /listing command."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} issued /listing command")
    try:
        all_cases = await Case.find({"status": CaseStatus.ADVERTISE}).to_list()
        logger.info(f"Fetched {len(all_cases)} ADVERTISE cases from the database")
        if not all_cases:
            await update.message.reply_text("No ADVERTISE cases found.")
            return State.END

        context.user_data["page"] = 1
        context.user_data["cases"] = all_cases
        paginated_cases, total_pages = paginate_list(all_cases, 1)

        keyboard = []
        for case in paginated_cases:
            row = [
                InlineKeyboardButton(
                    f"Case {case.case_no} - {case.person_name}",
                    callback_data=f"case_{str(case.id)}",
                )
            ]
            if case.user_id == user_id:
                row.append(
                    InlineKeyboardButton(
                        "📝 Edit", callback_data=f"edit_{str(case.id)}"
                    )
                )
                row.append(
                    InlineKeyboardButton(
                        "🗑 Delete", callback_data=f"delete_{str(case.id)}"
                    )
                )
            keyboard.append(row)

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

        await update.message.reply_text(
            "📋 **Select a Case to View Details:**",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return State.CASE_DETAILS
    except Exception as e:
        logger.error(f"Error in listing_command: {str(e)}\n{traceback.format_exc()}")
        await update.message.reply_text("An error occurred while fetching cases.")
        return State.END


async def case_details_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for displaying case details when a button is clicked."""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    try:
        case_id = query.data.removeprefix("case_")  # Extract case ID
        case = await Case.find_one({"_id": ObjectId(case_id)})
        print("THIS IS THE CASE", case)

        if not case:
            await query.message.edit_text("❌ Case not found.")
            return State.END  # Terminate the conversation

        # Fetch wallet and mobile number details
        wallet = await case.wallet.fetch() if case.wallet else None
        mobile_number = await case.mobile.fetch() if case.mobile else None

        # Format the case details
        case_message = (
            f"📌 **Case Details**\n"
            f"👤 **Person Name:** {case.person_name}\n"
            f"📍 **Last Seen Location:** {case.last_seen_location}\n"
            f"💰 **Reward:** {case.reward or 'None'} {case.reward_type or 'None'}\n"
            f"💼 **Wallet:** {wallet.public_key if wallet else 'Not provided'}\n"
            f"👤 **Gender:** {case.gender}\n"
            f"🧒 **Age:** {case.age}\n"
            f"📏 **Height:** {case.height} cm\n"
        )

        keyboard = []
        if case.user_id == user_id:
            row = [
                InlineKeyboardButton("📝 Edit", callback_data=f"edit_{str(case.id)}"),
                InlineKeyboardButton(
                    "🗑 Delete", callback_data=f"delete_{str(case.id)}"
                ),
            ]
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Edit the message to show case details
        await query.message.edit_text(
            case_message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        if case.user_id == user_id:
            return State.CASE_DETAILS

        return State.END  # Terminate the conversation

    except Exception as e:
        logger.error(
            f"Error in case_details_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text(
            "❌ An error occurred while fetching case details."
        )
        return State.END  # Terminate the conversation


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

            # Only show "Edit" and "Delete" buttons if the case belongs to the user
            if case.user_id == update.effective_user.id:
                row.append(
                    InlineKeyboardButton(
                        "📝 Edit", callback_data=f"edit_{str(case.id)}"
                    )
                )
                row.append(
                    InlineKeyboardButton(
                        "🗑 Delete", callback_data=f"delete_{str(case.id)}"
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
        return State.CASE_DETAILS
    except Exception as e:
        logger.error(
            f"Error in pagination_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text("❌ An error occurred while paginating cases.")
        return State.END


async def edit_case_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for editing a case."""
    query = update.callback_query
    await query.answer()

    # Extract case_id from callback data
    case_id = query.data.removeprefix("edit_")
    if "_" in case_id:
        case_id = case_id.split("_", maxsplit=1)[-1]  # Extract only the case ID

    print(f"Extracted case_id: {case_id}")

    # Validate case_id
    try:
        case_id = ObjectId(case_id)
    except errors.InvalidId:
        await query.message.edit_text("❌ Invalid case ID.")
        return State.END

    # Fetch the case from the database
    case = await Case.find_one({"_id": case_id})
    if not case:
        await query.message.edit_text("❌ Case not found.")
        return State.END

    user_id = update.effective_user.id
    if case.user_id != user_id:
        await query.message.edit_text("❌ You are not authorized to edit this case.")
        return State.END

    # Create a dynamic keyboard for all editable fields
    editable_fields = {
        "Name": "name",
        "Person Name": "person_name",
        "Relationship": "relationship",
        "Last Seen Location": "last_seen_location",
        "Gender": "gender",
        "Age": "age",
        "Hair Color": "hair_color",
        "Eye Color": "eye_color",
        "Height": "height",
        "Weight": "weight",
        "Distinctive Features": "distinctive_features",
        # "Status": "status",
        "Country": "country",
        "City": "city",
    }

    # Group buttons in rows of 2
    keyboard = [
        [
            InlineKeyboardButton(f"{k1}", callback_data=f"edit_field_{v1}_{case_id}"),
            InlineKeyboardButton(f"{k2}", callback_data=f"edit_field_{v2}_{case_id}"),
        ]
        for (k1, v1), (k2, v2) in zip(
            list(editable_fields.items())[::2], list(editable_fields.items())[1::2]
        )
    ]

    # If there's an odd number of fields, add the last button separately
    if len(editable_fields) % 2 != 0:
        last_key, last_value = list(editable_fields.items())[-1]
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{last_key}", callback_data=f"edit_field_{last_value}_{case_id}"
                )
            ]
        )

    # Add cancel button
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel_edit")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(
        "📝 **Which field would you like to edit?**",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return State.CASE_DETAILS


async def edit_field_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ask the user to enter a new value for the selected field."""
    query = update.callback_query
    await query.answer()

    # Extract field and case ID from callback data
    parts = query.data.split("_")
    field_name = "_".join(parts[1:-1])  # Join all parts except the first and last
    case_id = parts[-1]  # The last part is always the case ID

    print("Field name:", field_name, "Case ID:", case_id)

    # Store the case ID and field name in user_data for later use
    context.user_data["editing_case_id"] = case_id
    context.user_data["editing_field"] = field_name.split("_")[1]

    # Prompt the user to enter a new value for the field
    await query.message.edit_text(
        f"✏️ Please enter the new value for **{field_name.replace('_', ' ').title()}**: ",
        parse_mode="Markdown",
    )
    return State.EDIT_FIELD


async def update_case_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Update the specified field in the case document."""
    print("I'm Calling :smile")
    case_id = context.user_data.get("editing_case_id")
    field_name = context.user_data.get("editing_field")
    new_value = update.message.text.strip()

    print(f"CaseId: {case_id}, Field Name: {field_name}, New Value: {new_value}")

    if not case_id or not field_name:
        await update.message.reply_text("❌ Invalid request. Please try again.")
        return State.END

    # Fetch the case
    case = await Case.find_one({"_id": ObjectId(case_id)})
    if not case:
        await update.message.reply_text("❌ Case not found.")
        return State.END

    # Handle different types of fields
    try:
        if field_name in ["age", "height", "weight", "reward"]:
            new_value = float(new_value)
            if new_value < 0:
                raise ValueError("Value cannot be negative.")
        elif field_name == "status" and new_value.lower() not in ["draft", "advertise"]:
            raise ValueError("Status must be either 'draft' or 'advertise'.")
        elif field_name == "gender" and new_value.lower() not in [
            "male",
            "female",
            "other",
        ]:
            raise ValueError(
                "Invalid gender. Choose from 'male', 'female', or 'other'."
            )

        # Update the case document
        setattr(case, field_name, new_value)
        case.updated_at = datetime.utcnow()
        await case.save()

        await update.message.reply_text(
            f"✅ **{field_name.replace('_', ' ').title()}** updated to: **{new_value}**",
            parse_mode="Markdown",
        )
    except ValueError as e:
        await update.message.reply_text(f"❌ {str(e)} Please enter a valid value.")
        return State.EDIT_FIELD

    return State.END


async def delete_case_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for deleting a case."""
    query = update.callback_query
    await query.answer()
    try:
        case_id = query.data.removeprefix("delete_")  # Extract case ID
        case = await Case.find_one({"_id": ObjectId(case_id)})
        if not case:
            await query.message.edit_text("❌ Case not found.")
            return State.END

        # Check if the user owns the case
        user_id = update.effective_user.id
        if case.user_id != user_id:
            await query.message.edit_text(
                "❌ You are not authorized to delete this case."
            )
            return State.END

        # Delete the case from the database
        await Case.delete_one({"_id": ObjectId(case_id)})

        await query.message.edit_text("✅ Case has been successfully deleted.")

        # Refresh listing after deletion
        return await listing_command(update, context)

    except Exception as e:
        logger.error(
            f"Error in delete_case_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text("❌ An error occurred while deleting the case.")
        return State.END


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
        return State.END
    except Exception as e:
        logger.error(
            f"Error in cancel_edit_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text("❌ An error occurred while canceling the edit.")
        return State.END
