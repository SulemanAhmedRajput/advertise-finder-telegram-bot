import logging
import os
import math
import json
import base58
import pycountry
import geonamescache

import nest_asyncio
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =============== LOGGING & SETUP ===============
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
nest_asyncio.apply()


# =============== SOLANA CLIENT (OPTIONAL) ===============
# Only if you need Solana balance functionality.
try:
    from solders.keypair import Keypair
    from solana.rpc.api import Client
    from solders.pubkey import Pubkey

    SOLANA_NETWORK = "https://api.devnet.solana.com"
    client = Client(SOLANA_NETWORK)
except ImportError:
    logger.warning("Solana-related libraries not found. Some features may be disabled.")
    client = None

WALLETS_DIR = "wallets"


# =============== LANGUAGE DATA ===============
LANG_DATA = {
    "en": {
        "lang_choice": "English",
        "lang_button": "English",
        "start_msg": "Hello! Welcome to People Finder Bot.\nPlease select your language:",
        "choose_country": "Please enter your country name (partial name allowed):",
        "country_not_found": "No matching countries found. Please try again:",
        "country_multi": "Multiple countries found (Page {page} of {total}):",
        "country_selected": "You have selected",
        "disclaimer_title": "<b>Disclaimer</b>\n\n",
        "disclaimer_text": (
            "1. All bounties are held in escrow.\n"
            "2. AI-generated fake content is prohibited.\n"
            "3. For lawful, ethical use only.\n"
            "4. Report to authorities first when locating someone.\n"
            "5. We are not liable for misuse.\n"
            "6. Community-driven approach; verify carefully.\n"
            "7. We do not handle reward disputes.\n\n"
            "By using this bot, you agree to these terms."
        ),
        "agree_btn": "I Agree ✅",
        "disagree_btn": "I Disagree ❌",
        "disagree_end": "You did not agree. Conversation ended.",
        "enter_city": "Please enter your city name (partial name allowed):",
        "city_not_found": "No matching cities found. Please try again:",
        "city_multi": "Multiple cities found (Page {page} of {total}):",
        "city_selected": "City recorded:",
        "choose_action": "Would you like to Advertise or Find People?",
        "advertise_btn": "Advertise 📢",
        "find_btn": "Find People 👥",
        "find_dev": "Find People is under development.",
        "choose_wallet": "Please choose the type of wallet:",
        "sol_wallet": "Solana (SOL)",
        "btc_wallet": "Bitcoin (BTC)",
        "btc_dev": "BTC wallet creation is under development.",
        "wallet_name_prompt": "You've chosen Solana wallet.\nPlease enter a name for your wallet:",
        "wallet_name_empty": "Wallet name cannot be empty. Please try again:",
        "wallet_create_ok": "✅ Wallet Created Successfully!\n\n",
        "wallet_create_err": "❌ Error creating wallet.",
        "cancel_msg": "Operation cancelled. Use /start to begin again.",
        "invalid_choice": "Invalid choice. Conversation ended.",
    },
    "zh": {
        "lang_choice": "中文",
        "lang_button": "中文",
        "start_msg": "你好！欢迎使用 People Finder 机器人。\n请选择语言：",
        "choose_country": "请输入您的国家名称（支持模糊搜索）：",
        "country_not_found": "未找到匹配的国家。请重试：",
        "country_multi": "找到多个国家 (第 {page} 页，共 {total} 页)：",
        "country_selected": "您已选择",
        "disclaimer_title": "<b>免责声明</b>\n\n",
        "disclaimer_text": (
            "1. 所有悬赏由平台托管。\n"
            "2. 严禁使用 AI 虚假内容。\n"
            "3. 仅限合法合规使用。\n"
            "4. 寻人应先向当地警方或政府部门报备。\n"
            "5. 平台对任何滥用不承担责任。\n"
            "6. 社区互助，需自行核实。\n"
            "7. 平台不介入赏金纠纷。\n\n"
            "使用本机器人即表示您同意上述条款。"
        ),
        "agree_btn": "同意 ✅",
        "disagree_btn": "不同意 ❌",
        "disagree_end": "您不同意，结束对话。",
        "enter_city": "请输入您的城市名称（支持模糊搜索）：",
        "city_not_found": "未找到匹配的城市。请重试：",
        "city_multi": "找到多个城市 (第 {page} 页，共 {total} 页)：",
        "city_selected": "已记录城市：",
        "choose_action": "请选择：发布悬赏或寻找信息？",
        "advertise_btn": "发布悬赏 📢",
        "find_btn": "寻找信息 👥",
        "find_dev": "寻找信息功能正在开发中。",
        "choose_wallet": "请选择要创建的钱包类型：",
        "sol_wallet": "Solana (SOL)",
        "btc_wallet": "比特币 (BTC)",
        "btc_dev": "BTC 钱包功能正在开发中。",
        "wallet_name_prompt": "您选择了 Solana 钱包。\n请输入钱包名称：",
        "wallet_name_empty": "钱包名称不能为空，请重新输入：",
        "wallet_create_ok": "✅ 成功创建钱包！\n\n",
        "wallet_create_err": "❌ 创建钱包时出错。",
        "cancel_msg": "操作已取消。输入 /start 重新开始。",
        "invalid_choice": "无效选择，结束对话。",
    },
}


# Conversation states from the previous code
(
    SELECT_LANG,
    CHOOSE_COUNTRY,
    SHOW_DISCLAIMER,
    CHOOSE_CITY,
    CHOOSE_ACTION,
    CHOOSE_WALLET_TYPE,
    NAME_WALLET,
    CREATE_CASE_NAME,
    CREATE_CASE_MOBILE,
    CREATE_CASE_TAC,
    CREATE_CASE_DISCLAIMER,
    CREATE_CASE_REWARD_AMOUNT,
    CREATE_CASE_PERSON_DETAILS,
    CREATE_CASE_SUBMIT,
    END,
) = range(15)

# Additional states for Milestone 2
WALLET_MENU, WAITING_FOR_MOBILE = range(8, 10)
SETTINGS_MENU = 10  # We can also do range(9, 11) if you prefer

gc = geonamescache.GeonamesCache()
user_data_store = {}
ITEMS_PER_PAGE = 10

# =============== HELPER FUNCTIONS ===============


def get_text(user_id, key):
    """Get the localized text for a given key based on user language."""
    lang = user_data_store.get(user_id, {}).get("lang", "en")
    return LANG_DATA.get(lang, LANG_DATA["en"]).get(key, f"Undefined text for {key}")


def create_sol_wallet(wallet_name):
    """Create a SOL wallet with Keypair, store it as JSON, and return its details."""
    if not client:
        return None
    try:
        keypair = Keypair()
        public_key = str(keypair.pubkey())
        secret_key = base58.b58encode(bytes(keypair.to_bytes_array())).decode("utf-8")

        wallet = {
            "name": wallet_name,
            "public_key": public_key,
            "secret_key": secret_key,
        }

        if not os.path.exists(WALLETS_DIR):
            os.makedirs(WALLETS_DIR)

        wallet_filename = os.path.join(WALLETS_DIR, f"{public_key}.json")
        with open(wallet_filename, "w") as f:
            json.dump(wallet, f, indent=4)

        # Fetch balance
        balance_response = client.get_balance(Pubkey.from_string(public_key))
        balance_lamports = balance_response.value if balance_response else 0
        balance_sol = balance_lamports / 1e9
        wallet["balance_sol"] = balance_sol
        return wallet

    except Exception as e:
        logger.error(f"Error creating wallet: {e}", exc_info=True)
        return None


def load_user_wallet(user_id):
    """Load wallet info from user_data_store or from file if needed."""
    user_wallet = user_data_store[user_id].get("wallet")
    if not user_wallet:
        return None
    # Optionally re-check balance from the chain
    if client:
        pubkey = user_wallet.get("public_key")
        if pubkey:
            balance_response = client.get_balance(Pubkey.from_string(pubkey))
            balance_lamports = balance_response.value if balance_response else 0
            balance_sol = balance_lamports / 1e9
            user_wallet["balance_sol"] = balance_sol
    return user_wallet


def delete_user_wallet(user_id):
    """Remove the user's wallet from memory and optionally from disk."""
    user_wallet = user_data_store[user_id].get("wallet")
    if not user_wallet:
        return False
    # Delete from disk if you want
    pubkey = user_wallet.get("public_key")
    if pubkey:
        wallet_filename = os.path.join(WALLETS_DIR, f"{pubkey}.json")
        if os.path.exists(wallet_filename):
            os.remove(wallet_filename)
    user_data_store[user_id]["wallet"] = None
    return True


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


# =============== EXISTING CONVERSATION FLOW (START) ===============


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
        parse_mode=ParseMode.HTML,
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
        get_text(user_id, "choose_country"), parse_mode=ParseMode.HTML
    )
    return CHOOSE_COUNTRY


async def choose_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    txt = update.message.text.strip()
    matches = get_country_matches(txt)
    if not matches:
        await update.message.reply_text(
            get_text(user_id, "country_not_found"), parse_mode=ParseMode.HTML
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
            parse_mode=ParseMode.HTML,
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
            parse_mode=ParseMode.HTML,
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
            parse_mode=ParseMode.HTML,
        )
        user_data_store[user_id]["country_page"] = page_num
        return CHOOSE_COUNTRY
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML
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
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    return SHOW_DISCLAIMER


async def disclaimer_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "agree":
        await query.edit_message_text(
            get_text(user_id, "enter_city"), parse_mode=ParseMode.HTML
        )
        return CHOOSE_CITY
    else:
        await query.edit_message_text(
            get_text(user_id, "disagree_end"), parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END


async def choose_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    city_input = update.message.text.strip()
    country = user_data_store[user_id].get("country")
    if not country:
        await update.message.reply_text(
            get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END
    matches = get_city_matches(country, city_input)
    if not matches:
        await update.message.reply_text(
            get_text(user_id, "city_not_found"), parse_mode=ParseMode.HTML
        )
        return CHOOSE_CITY
    if len(matches) == 1:
        user_data_store[user_id]["city"] = matches[0]
        await update.message.reply_text(
            f"{get_text(user_id, 'city_selected')} {matches[0]}",
            parse_mode=ParseMode.HTML,
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
            parse_mode=ParseMode.HTML,
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
            f"{get_text(user_id, 'city_selected')} {city}", parse_mode=ParseMode.HTML
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
            parse_mode=ParseMode.HTML,
        )
        user_data_store[user_id]["city_page"] = page_num
        return CHOOSE_CITY
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML
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
        await query.edit_message_text(
            get_text(user_id, "find_dev"), parse_mode=ParseMode.HTML
        )
        return END
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END


async def wallet_type_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "SOL":
        await query.edit_message_text(
            get_text(user_id, "wallet_name_prompt"), parse_mode=ParseMode.HTML
        )
        return NAME_WALLET
    elif query.data == "BTC":
        await query.edit_message_text(
            get_text(user_id, "btc_dev"), parse_mode=ParseMode.HTML
        )
        return END
    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END


async def wallet_name_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    wallet_name = update.message.text.strip()
    if not wallet_name:
        await update.message.reply_text(
            get_text(user_id, "wallet_name_empty"), parse_mode=ParseMode.HTML
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
        await update.message.reply_text(msg, parse_mode=ParseMode.HTML)

        # Transition to the Create Case flow
        await update.message.reply_text(get_text(user_id, "create_case_title"))
        await update.message.reply_text(get_text(user_id, "enter_name"))
        return CREATE_CASE_NAME
    else:
        await update.message.reply_text(
            get_text(user_id, "wallet_create_err"), parse_mode=ParseMode.HTML
        )
        return END


async def create_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, "enter_name"))
    return CREATE_CASE_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    name = update.message.text.strip()
    context.user_data["case"] = {"name": name}
    await update.message.reply_text(get_text(user_id, "enter_mobile"))
    return CREATE_CASE_MOBILE


async def handle_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    mobile = update.message.text.strip()
    context.user_data["case"]["mobile"] = mobile

    await update.message.reply_text(get_text(user_id, "enter_tac"))
    await send_sms(mobile, "You are verified successfully as a person finder.")
    return CREATE_CASE_TAC


async def handle_tac(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    tac = update.message.text.strip()
    if tac == "123456":  # Replace with actual TAC verification logic
        await update.message.reply_text(get_text(user_id, "tac_verified"))
        await show_disclaimer_2(update, context)
        return CREATE_CASE_DISCLAIMER
    else:
        await update.message.reply_text(get_text(user_id, "tac_invalid"))
        return CREATE_CASE_TAC


async def show_disclaimer_2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
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
    await update.message.reply_text(
        get_text(user_id, "disclaimer_2"),
        reply_markup=kb,
    )
    return CREATE_CASE_DISCLAIMER


async def disclaimer_2_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "agree":
        await query.edit_message_text(get_text(user_id, "enter_reward_amount"))
        return CREATE_CASE_REWARD_AMOUNT
    else:
        await query.edit_message_text(get_text(user_id, "disagree_end"))
        return END


async def handle_reward_amount(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    reward = float(update.message.text.strip())
    if reward < 2:
        await update.message.reply_text(get_text(user_id, "insufficient_funds"))
        return CREATE_CASE_REWARD_AMOUNT
    context.user_data["case"]["reward"] = reward
    await update.message.reply_text(get_text(user_id, "enter_person_name"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_person_details(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    person_name = update.message.text.strip()
    context.user_data["case"]["person_name"] = person_name

    await update.message.reply_text(get_text(user_id, "relationship"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_relationship(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    relationship = update.message.text.strip()
    context.user_data["case"]["relationship"] = relationship
    await update.message.reply_text(get_text(user_id, "upload_photo"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"photos/{user_id}_photo.jpg"
    await photo_file.download_to_drive(photo_path)
    context.user_data["case"]["photo_path"] = photo_path
    await update.message.reply_text(get_text(user_id, "last_seen_location"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_last_seen_location(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    location = update.message.text.strip()
    context.user_data["case"]["last_seen_location"] = location
    await update.message.reply_text(get_text(user_id, "sex"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_sex(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    sex = update.message.text.strip()
    context.user_data["case"]["sex"] = sex
    await update.message.reply_text(get_text(user_id, "age"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    age = update.message.text.strip()
    context.user_data["case"]["age"] = age
    await update.message.reply_text(get_text(user_id, "hair_color"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_hair_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    hair_color = update.message.text.strip()
    context.user_data["case"]["hair_color"] = hair_color
    await update.message.reply_text(get_text(user_id, "eye_color"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_eye_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    eye_color = update.message.text.strip()
    context.user_data["case"]["eye_color"] = eye_color
    await update.message.reply_text(get_text(user_id, "height"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    height = update.message.text.strip()
    context.user_data["case"]["height"] = height
    await update.message.reply_text(get_text(user_id, "weight"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    weight = update.message.text.strip()
    context.user_data["case"]["weight"] = weight
    await update.message.reply_text(get_text(user_id, "distinctive_features"))
    return CREATE_CASE_PERSON_DETAILS


async def handle_distinctive_features(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    user_id = update.effective_user.id
    features = update.message.text.strip()
    context.user_data["case"]["distinctive_features"] = features
    await update.message.reply_text(get_text(user_id, "reason_for_finding"))
    return CREATE_CASE_PERSON_DETAILS


async def submit_case(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    case = context.user_data.get("case", {})
    case_no = (
        f"CASE-{user_id}-{len(context.user_data)}"  # Generate a unique case number
    )

    reward_amount = case.get("reward", 0)
    user_wallet = load_user_wallet(user_id)
    if user_wallet and user_wallet.get("balance_sol", 0) >= reward_amount:
        user_wallet["balance_sol"] -= reward_amount
        await update.message.reply_text(get_text(user_id, "escrow_transfer"))

    await update.message.reply_text(
        get_text(user_id, "case_submitted").format(case_no=case_no)
    )
    return END


async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kb = [
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_refresh"), callback_data="wallet_refresh"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_sol"), callback_data="wallet_sol"
            ),
            InlineKeyboardButton(
                get_text(user_id, "btn_btc"), callback_data="wallet_btc"
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_show_address"), callback_data="wallet_show"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_create_wallet"), callback_data="wallet_create"
            ),
            InlineKeyboardButton(
                get_text(user_id, "btn_delete_wallet"), callback_data="wallet_delete"
            ),
        ],
    ]
    await update.message.reply_text(
        get_text(user_id, "menu_wallet_title"),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML,
    )
    return WALLET_MENU


async def wallet_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    choice = query.data

    if choice == "wallet_refresh":
        user_wallet = load_user_wallet(user_id)
        if user_wallet:
            msg = get_text(user_id, "wallet_refreshed").format(
                name=user_wallet["name"],
                pub=user_wallet["public_key"],
                bal=user_wallet.get("balance_sol", 0),
            )
            await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(
                get_text(user_id, "wallet_no_exists"), parse_mode=ParseMode.HTML
            )
        return WALLET_MENU

    elif choice == "wallet_sol":
        await query.edit_message_text(
            "Selected SOL (placeholder).", parse_mode=ParseMode.HTML
        )
        return WALLET_MENU

    elif choice == "wallet_btc":
        await query.edit_message_text(
            "Selected BTC (placeholder).", parse_mode=ParseMode.HTML
        )
        return WALLET_MENU

    elif choice == "wallet_show":
        user_wallet = user_data_store[user_id].get("wallet")
        if user_wallet:
            msg = get_text(user_id, "wallet_exists").format(
                name=user_wallet["name"],
                pub=user_wallet["public_key"],
                bal=user_wallet.get("balance_sol", 0),
            )
            await query.edit_message_text(msg, parse_mode=ParseMode.HTML)
        else:
            await query.edit_message_text(
                get_text(user_id, "wallet_no_exists"), parse_mode=ParseMode.HTML
            )
        return WALLET_MENU

    elif choice == "wallet_create":
        await query.edit_message_text(
            get_text(user_id, "wallet_name_prompt"), parse_mode=ParseMode.HTML
        )
        return NAME_WALLET

    elif choice == "wallet_delete":
        success = delete_user_wallet(user_id)
        if success:
            await query.edit_message_text(
                get_text(user_id, "wallet_deleted"), parse_mode=ParseMode.HTML
            )
        else:
            await query.edit_message_text(
                get_text(user_id, "wallet_not_deleted"), parse_mode=ParseMode.HTML
            )
        return WALLET_MENU

    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    kb = [
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_language"), callback_data="settings_language"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_mobile_number"), callback_data="settings_mobile"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "btn_close_menu"), callback_data="settings_close"
            )
        ],
    ]
    await update.message.reply_text(
        get_text(user_id, "menu_settings_title"),
        reply_markup=InlineKeyboardMarkup(kb),
        parse_mode=ParseMode.HTML,
    )
    return SETTINGS_MENU


async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    choice = query.data

    if choice == "settings_language":
        kb = [
            [
                InlineKeyboardButton(
                    LANG_DATA["en"]["lang_button"], callback_data="setlang_en"
                ),
                InlineKeyboardButton(
                    LANG_DATA["zh"]["lang_button"], callback_data="setlang_zh"
                ),
            ]
        ]
        await query.edit_message_text(
            text="Choose your preferred language:",
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode=ParseMode.HTML,
        )
        return SETTINGS_MENU

    elif choice == "settings_mobile":
        await query.edit_message_text(
            get_text(user_id, "enter_mobile"), parse_mode=ParseMode.HTML
        )
        return WAITING_FOR_MOBILE

    elif choice == "settings_close":
        await query.edit_message_text(
            get_text(user_id, "btn_close_menu"), parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END

    elif choice.startswith("setlang_"):
        new_lang = choice.replace("setlang_", "")
        user_data_store[user_id]["lang"] = new_lang
        await query.edit_message_text(
            get_text(user_id, "lang_updated"), parse_mode=ParseMode.HTML
        )
        return SETTINGS_MENU

    else:
        await query.edit_message_text(
            get_text(user_id, "invalid_choice"), parse_mode=ParseMode.HTML
        )
        return ConversationHandler.END


async def mobile_number_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mobile = update.message.text.strip()
    user_data_store[user_id]["mobile_number"] = mobile
    msg = get_text(user_id, "mobile_saved").format(number=mobile)
    await update.message.reply_text(msg, parse_mode=ParseMode.HTML)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.message.reply_text(
        get_text(user_id, "cancel_msg"), reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        user_id = update.effective_user.id if update.effective_user else None
        if user_id:
            await update.effective_message.reply_text(
                get_text(user_id, "invalid_choice")
            )


def main():
    TOKEN = "7333467475:AAE-S2Hom4XZI_sfyCbrFrLkmXy6aQpL_GI"
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECT_LANG: [CallbackQueryHandler(select_lang_callback, pattern="^lang_")],
            CHOOSE_COUNTRY: [
                CallbackQueryHandler(
                    country_callback, pattern="^(country_select_|country_page_)"
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_country),
            ],
            SHOW_DISCLAIMER: [
                CallbackQueryHandler(disclaimer_callback, pattern="^(agree|disagree)$")
            ],
            CHOOSE_CITY: [
                CallbackQueryHandler(
                    city_callback, pattern="^(city_select_|city_page_)"
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_city),
            ],
            CHOOSE_ACTION: [
                CallbackQueryHandler(
                    action_callback, pattern="^(advertise|find_people)$"
                )
            ],
            CHOOSE_WALLET_TYPE: [
                CallbackQueryHandler(wallet_type_callback, pattern="^(SOL|BTC)$")
            ],
            NAME_WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_name_handler)
            ],
            CREATE_CASE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)
            ],
            CREATE_CASE_MOBILE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mobile)
            ],
            CREATE_CASE_TAC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tac)
            ],
            CREATE_CASE_DISCLAIMER: [
                CallbackQueryHandler(
                    disclaimer_2_callback, pattern="^(agree|disagree)$"
                )
            ],
            CREATE_CASE_REWARD_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reward_amount)
            ],
            CREATE_CASE_PERSON_DETAILS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_person_details)
            ],
            CREATE_CASE_SUBMIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, submit_case)
            ],
            END: [CommandHandler("start", start)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    wallet_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("wallet", wallet_command)],
        states={
            WALLET_MENU: [
                CallbackQueryHandler(
                    wallet_menu_callback,
                    pattern="^(wallet_refresh|wallet_sol|wallet_btc|wallet_show|wallet_create|wallet_delete)$",
                )
            ],
            NAME_WALLET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_name_handler)
            ],
            END: [CommandHandler("wallet", wallet_command)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        map_to_parent={},
    )

    settings_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_command)],
        states={
            SETTINGS_MENU: [
                CallbackQueryHandler(
                    settings_menu_callback,
                    pattern="^(settings_language|settings_mobile|settings_close|setlang_)",
                )
            ],
            WAITING_FOR_MOBILE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, mobile_number_handler)
            ],
            END: [CommandHandler("settings", settings_command)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        map_to_parent={},
    )

    application.add_handler(conv_handler)
    application.add_handler(wallet_conv_handler)
    application.add_handler(settings_conv_handler)
    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
