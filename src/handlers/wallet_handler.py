from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ConversationHandler,
    ContextTypes,
)

from constants import NAME_WALLET, WALLET_MENU, get_text, user_data_store
from utils.wallet import delete_user_wallet, load_user_wallet


async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /wallet command - shows an inline menu."""
    user_id = update.effective_user.id
    # Build the wallet menu inline keyboard
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
    """Handle the wallet menu button actions."""
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    choice = query.data

    # ---------------- REFRESH BALANCE ----------------
    if choice == "wallet_refresh":
        user_wallet = load_user_wallet(user_id)
        if user_wallet:
            # Show updated info
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

    # ---------------- SOL or BTC BUTTON (PLACEHOLDER) ----------------
    elif choice == "wallet_sol":
        # You could switch the user to a "default chain" = SOL if needed
        await query.edit_message_text(
            "Selected SOL (placeholder).", parse_mode=ParseMode.HTML
        )
        return WALLET_MENU

    elif choice == "wallet_btc":
        await query.edit_message_text(
            "Selected BTC (placeholder).", parse_mode=ParseMode.HTML
        )
        return WALLET_MENU

    # ---------------- SHOW ADDRESS ----------------
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

    # ---------------- CREATE WALLET ----------------
    elif choice == "wallet_create":
        # Move to the same logic used in the conversation (or do a simpler approach).
        await query.edit_message_text(
            get_text(user_id, "wallet_name_prompt"), parse_mode=ParseMode.HTML
        )
        return NAME_WALLET  # Reuse existing conversation state for naming

    # ---------------- DELETE WALLET ----------------
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
