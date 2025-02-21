import logging
from services.case_service import update_or_create_case
from services.wallet_service import WalletService
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from solders.pubkey import Pubkey
from services.wallet_service import solana_client
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
)
from constants import (
    State,
)
from services.user_service import get_user_lang, save_user_lang
from utils.wallet import create_sol_wallet
from utils.helper import get_city_matches, get_country_matches, paginate_list
from constant.language_constant import LANG_DATA, get_text, user_data_store


# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/start command entry point."""
    user_id = update.message.from_user.id

    # Check if the user's language preference is already saved
    user_lang = await get_user_lang(user_id)
    if user_lang:
        # Skip language selection if the user's preference is already set
        user_data_store[user_id] = {"lang": user_lang}
        context.user_data["lang"] = user_lang
        await update.message.reply_text(get_text(user_id, "choose_country"))
        return State.CHOOSE_COUNTRY

    # Show language selection buttons
    btns = [
        [
            InlineKeyboardButton(
                LANG_DATA["en"]["lang_button"], callback_data="lang_en"
            ),
            InlineKeyboardButton(
                LANG_DATA["zh"]["lang_button"], callback_data="lang_zh"
            ),
        ]
    ]
    await update.message.reply_text(
        f"{LANG_DATA['en']['start_msg']}\n\n{LANG_DATA['zh']['start_msg']}",
        reply_markup=InlineKeyboardMarkup(btns),
    )
    return State.SELECT_LANG


async def select_lang_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle language selection."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # Save the selected language to the database
    lang = data.replace("lang_", "")
    await save_user_lang(user_id, lang)

    # Update user data store
    user_data_store[user_id] = {"lang": lang}
    context.user_data["lang"] = lang

    await query.edit_message_text(get_text(user_id, "choose_country"))
    return State.CHOOSE_COUNTRY


async def choose_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
        await update_or_create_case(user_id, country=matches[0])
        await show_disclaimer(update, context)
        return State.SHOW_DISCLAIMER
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


async def country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    if data.startswith("country_select_"):

        country = data.replace("country_select_", "")
        context.user_data["country"] = country
        await update_or_create_case(user_id, country=country)

        await query.edit_message_text(
            f"{get_text(user_id, 'country_selected')} {country}.",
            parse_mode="HTML",
        )
        await show_disclaimer(update, context)
        return State.SHOW_DISCLAIMER
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


async def show_disclaimer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = (
        update.effective_user.id
        if update.message
        else update.callback_query.from_user.id
    )
    text = (
        f"{get_text(user_id, 'disclaimer_title')}{get_text(user_id, 'disclaimer_text')}"
    )
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
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, parse_mode="HTML", reply_markup=kb
        )
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    return State.SHOW_DISCLAIMER


async def disclaimer_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "agree":
        await query.edit_message_text(
            get_text(user_id, "enter_city"), parse_mode="HTML"
        )
        return State.CHOOSE_CITY
    else:
        await query.edit_message_text(
            get_text(user_id, "disagree_end"), parse_mode="HTML"
        )
        return State.END


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
        await update_or_create_case(user_id, city=matches[0])

        await update.message.reply_text(
            f"{get_text(user_id, 'city_selected')} {matches[0]}",
            parse_mode="HTML",
        )
        await choose_action(update, context)
        return State.CHOOSE_ACTION
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


async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = (
        update.effective_user.id
        if update.message
        else update.callback_query.from_user.id
    )
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    get_text(user_id, "advertise_btn"), callback_data="advertise"
                ),
                InlineKeyboardButton(
                    get_text(user_id, "find_btn"), callback_data="find_people"
                ),
            ]
        ]
    )
    if update.callback_query:
        await update.callback_query.message.reply_text(
            get_text(user_id, "choose_action"), reply_markup=kb
        )
    else:
        await update.message.reply_text(
            get_text(user_id, "choose_action"), reply_markup=kb
        )
    return State.CHOOSE_ACTION


async def action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    choice = query.data
    if choice == "advertise":
        # From the original code, it goes to CHOOSE_WALLET_TYPE
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        get_text(user_id, "sol_wallet"), callback_data="SOL"
                    ),
                    InlineKeyboardButton(
                        get_text(user_id, "usdt_wallet"), callback_data="USDT"
                    ),
                ]
            ]
        )
        await query.edit_message_text(
            get_text(user_id, "choose_wallet"), reply_markup=kb
        )
        return State.CHOOSE_WALLET_TYPE
    elif choice == "find_people":
        # Clearing the province
        await query.edit_message_text("Choose Province")
        return State.CHOOSE_PROVINCE
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return State.END


async def wallet_type_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "SOL":
        # Check if there are existing wallets
        existing_wallets = await WalletService.get_wallet_by_user(user_id)
        if existing_wallets:
            print(f"Existing wallets: {existing_wallets}")
            # Show existing wallets with an option to create a new one
            kb = [
                [
                    InlineKeyboardButton(
                        wallet.name, callback_data=f"wallet_{wallet.name}"
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
            return State.CHOOSE_WALLET_TYPE
        else:
            # Ask for the name of the wallet
            await query.edit_message_text(
                get_text(user_id, "wallet_name_prompt"), parse_mode="HTML"
            )
            return State.NAME_WALLET
    elif query.data == "USDT":
        await query.edit_message_text(get_text(user_id, "btc_dev"), parse_mode="HTML")
        return State.END
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return State.END


async def wallet_selection_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle the selection of an existing wallet."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Extract wallet name from callback data
    wallet_name = query.data.replace("wallet_", "")

    # Fetch wallet details (assuming WalletService can fetch by name)
    wallet_details = await WalletService.get_wallet_by_name(user_id, wallet_name)

    if wallet_details:
        total_sol = solana_client.get_balance(
            Pubkey.from_string(wallet_details["public_key"])
        )
        context.user_data["wallet"] = wallet_details  # Store in memory
        print(wallet_details["id"])
        await update_or_create_case(user_id, wallet=str(wallet_details["id"]))

        msg = get_text(user_id, "wallet_create_details").format(
            name=wallet_details["name"],
            public_key=wallet_details["public_key"],
            secret_key=wallet_details["private_key"],
            balance=total_sol,  # TODO: its must provide the proper balance
            wallet_type=wallet_details["wallet_type"],
        )

        await query.edit_message_text(msg, parse_mode="HTML")

        # Transition to the Create Case flow
        await query.message.reply_text(get_text(user_id, "create_case_title"))
        await query.message.reply_text(get_text(user_id, "enter_name"))
        return State.CREATE_CASE_NAME
    else:
        await query.edit_message_text(
            get_text(user_id, "wallet_not_found"), parse_mode="HTML"
        )
        return State.END


async def wallet_name_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle wallet name input and transition to Create Case flow."""
    user_id = update.effective_user.id

    # Check if the update is a callback query or a message
    if update.callback_query:
        # If it's a callback query, prompt the user to enter a wallet name
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            get_text(user_id, "wallet_name_prompt"), parse_mode="HTML"
        )
        return State.NAME_WALLET

    # If it's a text message, process the wallet name
    wallet_name = update.message.text.strip()

    if not wallet_name:
        await update.message.reply_text(
            get_text(user_id, "wallet_name_empty"), parse_mode="HTML"
        )
        return State.NAME_WALLET

    wallet_details = create_sol_wallet(wallet_name)
    wallet = await WalletService.create_wallet(user_id, "SOL", wallet_name)
    if wallet:
        # Get the total sol
        total_sol = solana_client.get_balance(Pubkey.from_string(wallet.public_key))
        context.user_data["wallet"] = wallet  # Store in memory
        msg = get_text(user_id, "wallet_create_details").format(
            name=wallet.name,
            public_key=wallet.public_key,
            secret_key=wallet.private_key,
            balance=total_sol.value,  # TODO: its must provide the proper balance
            wallet_type="SOL",
        )

        await update.message.reply_text(msg, parse_mode="HTML")

        # Transition to the Create Case flow
        await update.message.reply_text(get_text(user_id, "create_case_title"))
        await update.message.reply_text(get_text(user_id, "enter_name"))
        return State.CREATE_CASE_NAME
    else:
        await update.message.reply_text(
            get_text(user_id, "wallet_create_err"), parse_mode="HTML"
        )
        return State.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.message.reply_text(
        get_text(user_id, "cancel_msg"), reply_markup=ReplyKeyboardRemove()
    )
    return State.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger = logging.getLogger(__name__)
    logger.error("Exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        user_id = update.effective_user.id if update.effective_user else None
        if user_id:
            await update.effective_message.reply_text(
                get_text(user_id, "invalid_choice")
            )
