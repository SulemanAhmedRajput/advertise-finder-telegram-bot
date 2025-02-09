import handlers.finder_handler
import logging
import math
import pycountry
import geonamescache

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
)


from constants import (
    CHOOSE_ACTION,
    CHOOSE_CITY,
    CHOOSE_COUNTRY,
    CHOOSE_PROVINCE,
    CHOOSE_WALLET_TYPE,
    CREATE_CASE_NAME,
    CREATE_CASE_SUBMIT,
    END,
    ENTER_PRIVATE_KEY,
    get_text,
    ITEMS_PER_PAGE,
    LANG_DATA,
    NAME_WALLET,
    SELECT_LANG,
    SHOW_DISCLAIMER,
    user_data_store,
    WALLETS_DIR,
)
from utils.wallet import create_sol_wallet


gc = geonamescache.GeonamesCache()


def paginate_list(items, page, items_per_page=ITEMS_PER_PAGE):
    """Helper to paginate list items."""
    total_pages = max(1, math.ceil(len(items) / items_per_page)) if items else 1
    page = max(1, min(page, total_pages))
    start = (page - 1) * items_per_page
    end = start + items_per_page
    return items[start:end], total_pages


def get_country_matches(query):
    query = query.lower()
    return [c.name for c in pycountry.countries if query in c.name.lower()]


def get_cities_by_country(country_name):
    country = pycountry.countries.get(name=country_name)
    if not country:
        return []
    country_code = country.alpha_2
    all_cities = gc.get_cities().values()
    filtered = [city for city in all_cities if city["countrycode"] == country_code]
    if not filtered:
        return []
    sorted_cities = sorted(filtered, key=lambda x: x["population"], reverse=True)
    return [city["name"] for city in sorted_cities[:50]]


def get_city_matches(country_name, query):
    return [
        c for c in get_cities_by_country(country_name) if query.lower() in c.lower()
    ]


# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """/start command entry point."""
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
        f"{LANG_DATA['en']['start_msg']}\n\n" f"{LANG_DATA['zh']['start_msg']}",
        reply_markup=InlineKeyboardMarkup(btns),
        parse_mode="HTML",
    )
    return SELECT_LANG


async def select_lang_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle language selection."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    if data == "lang_en":
        user_data_store[user_id] = {"lang": "en"}
    elif data == "lang_zh":
        user_data_store[user_id] = {"lang": "zh"}
    else:
        user_data_store[user_id] = {"lang": "en"}
    await query.edit_message_text(
        get_text(user_id, "choose_country"), parse_mode="HTML"
    )
    # return CREATE_CASE_SUBMIT
    return CHOOSE_COUNTRY


# TODO - TESTING THE COUNTRY CHOOSING
async def choose_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    txt = update.message.text.strip()
    matches = get_country_matches(txt)
    if not matches:
        await update.message.reply_text(
            get_text(user_id, "country_not_found"), parse_mode="HTML"
        )
        return CHOOSE_COUNTRY
    if len(matches) == 1:
        user_data_store[user_id]["country"] = matches[0]
        await show_disclaimer(update, context)
        return SHOW_DISCLAIMER
    else:
        user_data_store[user_id]["country_matches"] = matches
        user_data_store[user_id]["country_page"] = 1
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
        return CHOOSE_COUNTRY


async def country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    if data.startswith("country_select_"):
        country = data.replace("country_select_", "")
        user_data_store[user_id]["country"] = country
        await query.edit_message_text(
            f"{get_text(user_id, 'country_selected')} {country}.",
            parse_mode="HTML",
        )
        await show_disclaimer(update, context)
        return SHOW_DISCLAIMER
    elif data.startswith("country_page_"):
        page_str = data.replace("country_page_", "")
        try:
            page_num = int(page_str)
            if page_num < 1:
                page_num = 1
        except ValueError:
            page_num = 1
        matches = user_data_store[user_id].get("country_matches", [])
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
        user_data_store[user_id]["country_page"] = page_num
        return CHOOSE_COUNTRY
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return ConversationHandler.END


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
    return SHOW_DISCLAIMER


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
        return CHOOSE_CITY
    else:
        await query.edit_message_text(
            get_text(user_id, "disagree_end"), parse_mode="HTML"
        )
        return END


async def choose_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city_input = update.message.text.strip()
    country = user_data_store[user_id].get("country")
    if not country:
        await update.message.reply_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return ConversationHandler.END
    matches = get_city_matches(country, city_input)
    if not matches:
        await update.message.reply_text(
            get_text(user_id, "city_not_found"), parse_mode="HTML"
        )
        return CHOOSE_CITY
    if len(matches) == 1:
        user_data_store[user_id]["city"] = matches[0]
        await update.message.reply_text(
            f"{get_text(user_id, 'city_selected')} {matches[0]}",
            parse_mode="HTML",
        )
        await choose_action(update, context)
        return CHOOSE_ACTION
    else:
        user_data_store[user_id]["city_matches"] = matches
        user_data_store[user_id]["city_page"] = 1
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
        return CHOOSE_CITY


async def city_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    if data.startswith("city_select_"):
        city = data.replace("city_select_", "")
        user_data_store[user_id]["city"] = city
        await query.edit_message_text(
            f"{get_text(user_id, 'city_selected')} {city}", parse_mode="HTML"
        )
        await choose_action(update, context)
        return CHOOSE_ACTION
    elif data.startswith("city_page_"):
        page_str = data.replace("city_page_", "")
        try:
            page_num = int(page_str)
            if page_num < 1:
                page_num = 1
        except ValueError:
            page_num = 1
        matches = user_data_store[user_id].get("city_matches", [])
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
        user_data_store[user_id]["city_page"] = page_num
        return CHOOSE_CITY
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return ConversationHandler.END


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
    return CHOOSE_ACTION


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
                        get_text(user_id, "btc_wallet"), callback_data="BTC"
                    ),
                ]
            ]
        )
        await query.edit_message_text(
            get_text(user_id, "choose_wallet"), reply_markup=kb
        )
        return CHOOSE_WALLET_TYPE
    elif choice == "find_people":
        await query.edit_message_text("Select a province:", parse_mode="HTML")
        return await handlers.finder.choose_province(update, context)
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return END


async def wallet_type_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "SOL":
        await query.edit_message_text(
            get_text(user_id, "wallet_name_prompt"), parse_mode="HTML"
        )
        return NAME_WALLET
    elif query.data == "BTC":
        await query.edit_message_text(get_text(user_id, "btc_dev"), parse_mode="HTML")
        return END
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode="HTML"
        )
        return ConversationHandler.END


async def wallet_name_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle wallet name input and transition to Create Case flow."""
    user_id = update.effective_user.id
    wallet_name = update.message.text.strip()
    if not wallet_name:
        await update.message.reply_text(
            get_text(user_id, "wallet_name_empty"), parse_mode="HTML"
        )
        return NAME_WALLET

    wallet_details = create_sol_wallet(wallet_name)
    if wallet_details:
        user_data_store[user_id]["wallet"] = wallet_details  # Store in memory
        msg = (
            f"{get_text(user_id, 'wallet_create_ok')}"
            f"Name: {wallet_details['name']}\n"
            f"Public Key: {wallet_details['public_key']}\n"
            f"Secret Key: {wallet_details['secret_key']}\n"
            f"Balance: {wallet_details['balance_sol']} SOL"
        )

        print("Hello there i am from the wallet name handler function")
        await update.message.reply_text(msg, parse_mode="HTML")

        # Transition to the Create Case flow
        await update.message.reply_text(get_text(user_id, "create_case_title"))
        await update.message.reply_text(get_text(user_id, "enter_name"))
        return CREATE_CASE_NAME
    else:
        await update.message.reply_text(
            get_text(user_id, "wallet_create_err"), parse_mode="HTML"
        )
        return END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.message.reply_text(
        get_text(user_id, "cancel_msg"), reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger = logging.getLogger(__name__)
    logger.error("Exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        user_id = update.effective_user.id if update.effective_user else None
        if user_id:
            await update.effective_message.reply_text(
                get_text(user_id, "invalid_choice")
            )


# Setup logging
def setup_logging():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.FileHandler("bot.log"),  # Log to a file named bot.log
            logging.StreamHandler(),  # Also log to the console
        ],
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging setup complete.")
