import logging
from datetime import datetime
from beanie import PydanticObjectId
from config.config_manager import OWNER_TELEGRAM_ID, STAKE_WALLET_PRIVATE_KEY
from constant.language_constant import get_text, user_data_store
from constants import State
from models.case_model import Case, CaseStatus
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ContextTypes,
)
from bson import ObjectId, errors
import traceback
from models.finder_model import Finder, FinderStatus
from services.case_service import update_case
from services.finder_service import FinderService
from services.user_service import get_user_lang
from services.wallet_service import WalletService
from utils.logger import logger
from utils.error_wrapper import catch_async
from utils.helper import get_city_matches, get_country_matches, paginate_list


@catch_async
async def listing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for the /listing command."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} issued /listing command")
    all_cases = (
        await Case.find({"status": CaseStatus.ADVERTISE, "deleted": False})
        .sort(-Case.created_at)  # Sorting in descending order
        .to_list()
    )

    logger.info(f"Fetched {len(all_cases)} ADVERTISE cases from the database")
    user_lang = await get_user_lang(user_id)
    if user_lang:
        user_data_store[user_id] = {"lang": user_lang}
        context.user_data["lang"] = user_lang
    if not all_cases:
        await update.message.reply_text(get_text(user_id, "no_advertise_cases"))
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
        finder_exist = await Finder.find(
            {"case.$id": PydanticObjectId(case.id)}
        ).to_list()

        if case.user_id == user_id and len(finder_exist) == 0:
            row.append(
                InlineKeyboardButton(
                    get_text(user_id, "edit_button"),
                    callback_data=f"edit_{str(case.id)}",
                )
            )
            row.append(
                InlineKeyboardButton(
                    get_text(user_id, "delete_button"),
                    callback_data=f"delete_{str(case.id)}",
                )
            )

        print(user_id, OWNER_TELEGRAM_ID)

        if str(user_id) == str(OWNER_TELEGRAM_ID) and finder_exist:
            row.append(
                InlineKeyboardButton(
                    # get_text(user_id, "reward_button"),
                    "Reward Button",
                    callback_data=f"reward_{str(case.id)}",
                )
            )
        keyboard.append(row)

    navigation_buttons = []
    current_page = context.user_data["page"]
    if current_page > 1:
        navigation_buttons.append(
            InlineKeyboardButton(
                get_text(user_id, "previous_button"), callback_data="page_previous"
            )
        )
    if current_page < total_pages:
        navigation_buttons.append(
            InlineKeyboardButton(
                get_text(user_id, "next_button"), callback_data="page_next"
            )
        )
    if navigation_buttons:
        keyboard.append(navigation_buttons)
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_text(user_id, "select_case_details"),
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return State.CASE_DETAILS


@catch_async
async def case_details_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for displaying case details when a button is clicked."""
    user_id = update.effective_user.id
    query = update.callback_query
    await query.answer()

    try:
        case_id = query.data.removeprefix("case_")  # Extract case ID
        case = await Case.find_one({"_id": PydanticObjectId(case_id), "deleted": False}, fetch_links=True)
        print("THIS IS THE CASE", case)

        if not case:
            await query.message.edit_text(get_text(user_id, "case_not_found"))
            return State.END  # Terminate the conversation

        # Fetch wallet and mobile number details if they exist

        # Format the case details using the constant template
        proof_text = (
            f"[Proof]({case.case_photo})"
            if case.case_photo and case.case_photo.startswith("http")
            else "No proof available"
        )

        case_message = get_text(
            user_id,
            "case_details_template",
        ).format(
            person_name=case.person_name,
            last_seen_location=case.last_seen_location,
            reward=case.reward or "None",
            reward_type=case.reward_type or "None",
            wallet="wallet",  # TODO: its remains
            gender=case.gender,
            age=case.age,
            height=case.height,
        )

        case_message += f"\n\n**Proof:** {proof_text}"

        keyboard = []
        if case.user_id == user_id:
            row = [
                InlineKeyboardButton(
                    get_text(user_id, "edit_button"),
                    callback_data=f"edit_{str(case.id)}",
                ),
                InlineKeyboardButton(
                    get_text(user_id, "delete_button"),
                    callback_data=f"delete_{str(case.id)}",
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
        await query.message.edit_text(get_text(user_id, "error_fetching_case_details"))
        return State.END  # Terminate the conversation


@catch_async
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
        user_id = update.effective_user.id

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
                    f"Case {case.case_no} - {case.name}",
                    callback_data=f"case_{str(case.id)}",
                )
            ]

            finder_exist = await Finder.find(
                {"case.$id": PydanticObjectId(case.id)}
            ).to_list()
            print(f"Finder exist: {finder_exist}")
            if case.user_id == update.effective_user.id and len(finder_exist) == 0:

                row.append(
                    InlineKeyboardButton(
                        get_text(user_id, "edit_button"),
                        callback_data=f"edit_{str(case.id)}",
                    )
                )
                row.append(
                    InlineKeyboardButton(
                        get_text(user_id, "delete_button"),
                        callback_data=f"delete_{str(case.id)}",
                    )
                )

            #
            keyboard.append(row)

        # Add navigation buttons
        navigation_buttons = []
        if new_page > 1:
            navigation_buttons.append(
                InlineKeyboardButton(
                    get_text(user_id, "previous_button"), callback_data="page_previous"
                )
            )
        if new_page < total_pages:
            navigation_buttons.append(
                InlineKeyboardButton(
                    get_text(user_id, "next_button"), callback_data="page_next"
                )
            )
        if navigation_buttons:
            keyboard.append(navigation_buttons)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Edit the message with the updated case list
        await query.message.edit_text(
            get_text(user_id, "select_case_details"),
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return State.CASE_DETAILS
    except Exception as e:
        logger.error(
            f"Error in pagination_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text(get_text(user_id, "error_paginating_cases"))
        return State.END


@catch_async
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
        await query.message.edit_text(get_text(user_id, "invalid_case_id"))
        return State.END

    # Fetch the case from the database
    case = await Case.find_one({"_id": case_id})
    if not case:
        await query.message.edit_text(get_text(user_id, "case_not_found"))
        return State.END

    user_id = update.effective_user.id
    if case.user_id != user_id:
        await query.message.edit_text(get_text(user_id, "not_authorized_edit"))
        return State.END

    # Fetch editable fields based on the user's language
    editable_fields = get_text(user_id, "editable_fields")

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
    keyboard.append(
        [
            InlineKeyboardButton(
                get_text(user_id, "cancel_edit_button"), callback_data="cancel_edit"
            )
        ]
    )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_text(
        get_text(user_id, "edit_field_prompt"),
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    return State.CASE_DETAILS


@catch_async
async def edit_field_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ask the user to enter a new value for the selected field."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    # Extract field and case ID from callback data
    callback_data = query.data.removeprefix("edit_field_")
    last_underscore_index = callback_data.rfind("_")
    field_name = callback_data[:last_underscore_index]  # Extract field name correctly
    case_id = callback_data[last_underscore_index + 1 :]  # Extract case ID

    print("Field name:", field_name, "Case ID:", case_id)

    # Store the case ID and field name in user_data for later use
    context.user_data["editing_case_id"] = case_id
    context.user_data["editing_field"] = field_name  # Keep full field name

    # Prompt the user to enter a new value for the field
    await query.message.edit_text(
        get_text(user_id, "enter_new_value").format(
            field_name=field_name.replace("_", " ").title()
        ),
        parse_mode="Markdown",
    )
    return State.EDIT_FIELD


@catch_async
async def update_case_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Update the specified field in the case document."""
    print("I'm Calling :smile")
    case_id = context.user_data.get("editing_case_id")
    field_name = context.user_data.get("editing_field")  # Use full field name
    user_id = update.effective_user.id
    new_value = update.message.text.strip()

    print(f"CaseId: {case_id}, Field Name: {field_name}, New Value: {new_value}")

    if not case_id or not field_name:
        await update.message.reply_text(get_text(user_id, "invalid_request"))
        return State.END

    # Fetch the case
    case = await Case.find_one({"_id": PydanticObjectId(case_id)})
    if not case:
        await update.message.reply_text(get_text(user_id, "case_not_found"))
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
        setattr(case, field_name, new_value)  # Ensure it updates correctly
        case.updated_at = datetime.utcnow()
        await case.save()

        await update.message.reply_text(
            get_text(
                user_id,
                "field_updated_successfully",
            ).format(
                field_name=field_name.replace("_", " ").title(),
                new_value=new_value,
            ),
            parse_mode="Markdown",
        )
    except ValueError as e:
        await update.message.reply_text(
            get_text(user_id, "invalid_value").format(error_message=str(e))
        )
        return State.EDIT_FIELD

    return State.END


@catch_async
async def update_choose_country(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    txt = update.message.text.strip()
    matches = get_country_matches(txt)
    if not matches:
        await update.message.reply_text(
            get_text(user_id, "country_not_found"), parse_mode="HTML"
        )
        return State.CHOOSE_COUNTRY
    if len(matches) == 1:
        context.user_data["country"] = matches[0]
        # Choose the country
        await update.message.reply_text("Choose a city:")
        return State.CHOOSE_CITY
    else:

        context.user_data["country_matches"] = matches
        context.user_data["country_page"] = 1

        paginated, total = paginate_list(matches, 1)
        kb = []
        for c in paginated:
            kb.append([InlineKeyboardButton(c, callback_data=f"country_select_{c}")])
        # Pagination buttons
        if total > 1:
            kb.append(
                [
                    InlineKeyboardButton("⬅️", callback_data="country_page_0"),
                    InlineKeyboardButton("➡️", callback_data="country_page_2"),
                ]
            )
        markup = InlineKeyboardMarkup(kb)
        await update.message.reply_text(
            get_text(user_id, "country_multi").format(page=1, total=total),
            reply_markup=markup,
            parse_mode="HTML",
        )
        return State.CHOOSE_COUNTRY


@catch_async
async def country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    if data.startswith("country_select_"):

        country = data.replace("country_select_", "")
        context.user_data["country"] = country

        await query.edit_message_text(
            f"{get_text(user_id, 'country_selected')} {country}.",
            parse_mode="HTML",
        )
        # Choose the country
        await update.message.reply_text("Choose a city:")
        return State.CHOOSE_CITY
    elif data.startswith("country_page_"):
        page_str = data.replace("country_page_", "")
        try:
            page_num = int(page_str)
            if page_num < 1:
                page_num = 1
        except ValueError:
            page_num = 1
        matches = context.user_data.get("country_matches", [])
        paginated, total = paginate_list(matches, page_num)
        kb = []
        for c in paginated:
            kb.append([InlineKeyboardButton(c, callback_data=f"country_select_{c}")])
        nav_row = []
        if page_num > 1:
            nav_row.append(
                InlineKeyboardButton("⬅️", callback_data=f"country_page_{page_num-1}")
            )
        if page_num < total:
            nav_row.append(
                InlineKeyboardButton("➡️", callback_data=f"country_page_{page_num+1}")
            )
        if nav_row:
            kb.append(nav_row)
        markup = InlineKeyboardMarkup(kb)
        await query.edit_message_text(
            get_text(user_id, "country_multi").format(page=page_num, total=total),
            reply_markup=markup,
            parse_mode="HTML",
        )

        context.user_data["country_page"] = page_num
        return State.CHOOSE_COUNTRY
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return State.END


@catch_async
async def choose_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city_input = update.message.text.strip()
    country = context.user_data.get("country")
    if not country:
        await update.message.reply_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return State.END
    matches = get_city_matches(country, city_input)
    if not matches:
        await update.message.reply_text(
            get_text(user_id, "city_not_found"), parse_mode="HTML"
        )
        return State.CHOOSE_CITY
    if len(matches) == 1:
        context.user_data["city"] = matches[0]
        await update.message.reply_text(
            f"{get_text(user_id, 'city_selected')} {matches[0]}",
            parse_mode="HTML",
        )
        update.message.reply_text("Updated Successfully")
        return State.END
    else:
        context.user_data["city_matches"] = matches
        context.user_data["city_page"] = 1
        paginated, total = paginate_list(matches, 1)
        kb = []
        for c in paginated:
            kb.append([InlineKeyboardButton(c, callback_data=f"city_select_{c}")])
        # Pagination
        if total > 1:
            kb.append(
                [
                    InlineKeyboardButton("⬅️", callback_data="city_page_0"),
                    InlineKeyboardButton("➡️", callback_data="city_page_2"),
                ]
            )
        markup = InlineKeyboardMarkup(kb)
        await update.message.reply_text(
            get_text(user_id, "city_multi").format(page=1, total=total),
            reply_markup=markup,
            parse_mode="HTML",
        )
        return State.CHOOSE_CITY


@catch_async
async def city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    if data.startswith("city_select_"):
        city = data.replace("city_select_", "")
        context.user_data["city"] = city
        await update_or_create_case(user_id, city=city)

        await query.edit_message_text(
            f"{get_text(user_id, 'city_selected')} {city}", parse_mode="HTML"
        )
        await choose_action(update, context)
        return State.CHOOSE_ACTION
    elif data.startswith("city_page_"):
        page_str = data.replace("city_page_", "")
        try:
            page_num = int(page_str)
            if page_num < 1:
                page_num = 1
        except ValueError:
            page_num = 1
        matches = context.user_data.get("city_matches", [])
        paginated, total = paginate_list(matches, page_num)
        kb = []
        for c in paginated:
            kb.append([InlineKeyboardButton(c, callback_data=f"city_select_{c}")])
        nav_row = []
        if page_num > 1:
            nav_row.append(
                InlineKeyboardButton("⬅️", callback_data=f"city_page_{page_num-1}")
            )
        if page_num < total:
            nav_row.append(
                InlineKeyboardButton("➡️", callback_data=f"city_page_{page_num+1}")
            )
        if nav_row:
            kb.append(nav_row)
        markup = InlineKeyboardMarkup(kb)
        await query.edit_message_text(
            get_text(user_id, "city_multi").format(page=page_num, total=total),
            reply_markup=markup,
            parse_mode="HTML",
        )
        context.user_data["city_page"] = page_num
        return State.CHOOSE_CITY
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return State.END


# ------------------------ Delete Case Start ------------------------


@catch_async
async def delete_case_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler for confirming and soft deleting a case."""
    query = update.callback_query
    await query.answer()

    try:
        case_id = query.data.removeprefix("delete_")  # Extract case ID
        user_id = update.effective_user.id

        # Check if user is confirming deletion
        if case_id.startswith("confirm_"):
            case_id = case_id.removeprefix("confirm_")
            case = await Case.find_one({"_id": PydanticObjectId(case_id)})
            
            if not case:
                await query.edit_message_text(get_text(user_id, "case_not_found"))
                return State.END

            if case.user_id != user_id:
                await query.edit_message_text(get_text(user_id, "not_authorized_delete"))
                return State.END

            # Soft delete: update `deleted` field to `True`
            await update_case(
                case_id = PydanticObjectId(case_id),
                deleted = True                  
            )

            await query.edit_message_text(get_text(user_id, "case_deleted_successfully"))

            # Refresh listing after deletion
            return await listing_command(update, context)

        # Ask for confirmation before soft deleting
        keyboard = [
            [
                InlineKeyboardButton(get_text(user_id, "yes"), callback_data=f"delete_confirm_{case_id}"),
                InlineKeyboardButton(get_text(user_id, "no"), callback_data="delete_cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Check if message exists before editing
        if query.message:
            await query.edit_message_text(get_text(user_id, "confirm_delete"), reply_markup=reply_markup)
        else:
            await context.bot.send_message(chat_id=user_id, text=get_text(user_id, "confirm_delete"), reply_markup=reply_markup)

        return State.CASE_DETAILS

    except Exception as e:
        logger.error(f"Error in delete_case_callback: {str(e)}\n{traceback.format_exc()}")
        await query.edit_message_text(get_text(update.effective_user.id, "error_deleting_case"))
        return State.END


@catch_async
async def cancel_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handler to cancel delete request."""
    query = update.callback_query
    await query.answer()

    try:
        if query.message:
            await query.edit_message_text(get_text(update.effective_user.id, "delete_cancelled"))
        else:
            await context.bot.send_message(chat_id=update.effective_user.id, text=get_text(update.effective_user.id, "delete_cancelled"))
    except Exception as e:
        logger.error(f"Error in cancel_delete_callback: {str(e)}")

    return State.END
    
    
# ------------------------ Delete Case End ------------------------

@catch_async
async def cancel_edit_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handler for canceling the edit process."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    try:
        # Clear any edit-related data from context
        context.user_data.pop("edit_case_id", None)
        context.user_data.pop("edit_field", None)

        # Return to the case listing
        await query.message.edit_text(get_text(user_id, "edit_canceled"))
        return State.END
    except Exception as e:
        logger.error(
            f"Error in cancel_edit_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text(get_text(user_id, "error_canceling_edit"))
        return State.END


@catch_async
async def reward_case_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles the reward process when advertiser clicks 'Reward'."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    case_id = query.data.removeprefix("reward_")

    try:
        case = await Case.find_one({"_id": ObjectId(case_id)})
        if not case:
            await query.message.edit_text(get_text(user_id, "case_not_found"))
            return State.END

        # if case.user_id != user_id:
        #     await query.message.edit_text(get_text(user_id, "not_authorized_reward"))
        #     return State.END

        # Get all finders for this case
        finders = await Finder.find({"case.$id": PydanticObjectId(case.id)}).to_list()
        if not finders:
            await query.message.edit_text(get_text(user_id, "no_finders_for_case"))
            return State.END

        # Show finders with details
        message = get_text(user_id, "finder_list_header") + "\n\n"
        keyboard = []

        for finder in finders:
            proof_text = (
                "\n".join(f"[Proof]({url})" for url in finder.proof_url)
                if finder.proof_url
                else "No proof available"
            )
            message += f"👤 *Finder ID:* `{finder.user_id}`\n📍 *Location:* {finder.reported_location}\n📎 *Proof:* {proof_text}\n\n"

            keyboard.append(
                [
                    InlineKeyboardButton(
                        get_text(user_id, "reward_this_finder"),
                        callback_data=f"send_reward_{finder.user_id}_{case.id}",
                    )
                ]
            )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(
            message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )
        return State.CASE_DETAILS

    except Exception as e:
        logger.error(
            f"Error in reward_case_callback: {str(e)}\n{traceback.format_exc()}"
        )
        await query.message.edit_text(get_text(user_id, "error_processing_reward"))
        return State.END


@catch_async
async def ask_reward_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Asks advertiser how much reward they want to send."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data.removeprefix("send_reward_")
    finder_id, case_id = callback_data.split("_")

    try:
        case = await Case.find_one({"_id": ObjectId(case_id)})
        finder = await Finder.find_one(
            {"user_id": int(finder_id), "case.$id": PydanticObjectId(case.id)}
        )

        if not case or not finder:
            await query.message.edit_text(get_text(user_id, "case_or_finder_not_found"))
            return State.END

        context.user_data["reward_case_id"] = case.id
        context.user_data["reward_finder_id"] = finder.user_id

        await query.message.edit_text(
            get_text(user_id, "enter_reward_amount").format(max_amount=case.reward),
            parse_mode="Markdown",
        )
        return State.EDIT_FIELD  # Next step: user enters amount

    except Exception as e:
        logger.error(f"Error in ask_reward_amount: {str(e)}\n{traceback.format_exc()}")
        await query.message.edit_text(get_text(user_id, "error_asking_reward_amount"))
        return State.END


# Modify process_reward_transfer to show confirmation:
@catch_async
async def process_reward_transfer(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Shows confirmation before processing reward transfer"""
    user_id = update.effective_user.id
    amount = update.message.text.strip()
    case_id = context.user_data.get("reward_case_id")
    finder_id = context.user_data.get("reward_finder_id")

    try:
        case = await Case.find_one({"_id": ObjectId(case_id)})
        if not case:
            await update.message.reply_text(get_text(user_id, "case_not_found"))
            return State.END

        # Validate amount
        amount = float(amount)
        if amount <= 0 or amount > case.reward:
            raise ValueError("Invalid amount")

        # Store confirmation data
        context.user_data["reward_amount"] = amount

        # Show confirmation buttons
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        get_text(user_id, "confirm_button"),
                        callback_data="confirm_reward",
                    ),
                    InlineKeyboardButton(
                        get_text(user_id, "cancel_button"),
                        callback_data="cancel_reward",
                    ),
                ]
            ]
        )

        await update.message.reply_text(
            get_text(user_id, "reward_confirmation").format(
                amount=amount, finder_id=finder_id, case_no=case.case_no
            ),
            reply_markup=keyboard,
            parse_mode="Markdown",
        )
        return State.CONFIRM_REWARD

    except ValueError:
        await update.message.reply_text(
            get_text(user_id, "invalid_reward_amount").format(max_amount=case.reward)
        )
        return State.EDIT_FIELD


# New confirmation handler
@catch_async
async def confirm_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Executes the reward transfer after confirmation"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        case_id = context.user_data.get("reward_case_id")
        finder_id = context.user_data.get("reward_finder_id")
        amount = context.user_data.get("reward_amount")

        case = await Case.find_one({"_id": ObjectId(case_id)})

        print(f"Case: {case}")

        finder = await Finder.find_one(
            {"user_id": int(finder_id), "case.$id": PydanticObjectId(case.id)}
        )

        print(f"Finder: {finder}")

        # Perform transfer

        finder_wallet = await finder.wallet.fetch(fetch_links=True)

        await WalletService.send_sol(
            STAKE_WALLET_PRIVATE_KEY, finder_wallet.public_key, amount
        )

        finder.status = FinderStatus.COMPLETED
        case.status = CaseStatus.COMPLETED
        await case.save()

        await finder.save()

        await query.message.edit_text(
            get_text(user_id, "reward_success").format(
                amount=amount, finder_id=finder.user_id
            )
        )
        return State.END

    except Exception as e:
        logger.error(f"Reward confirmation error: {str(e)}")
        await query.message.edit_text(get_text(user_id, "error_transferring_reward"))
        return State.END


# New cancellation handler
@catch_async
async def cancel_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels the reward process"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    context.user_data.pop("reward_case_id", None)
    context.user_data.pop("reward_finder_id", None)
    context.user_data.pop("reward_amount", None)

    await query.message.edit_text(get_text(user_id, "reward_cancelled"))
    return State.END
