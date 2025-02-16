from services.wallet_service import WalletService
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

from constants import CREATE_WALLET, NAME_WALLET, WALLET_MENU, get_text, user_data_store
from utils.wallet import delete_user_wallet, load_user_wallet


async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /wallet command."""
    user_id = update.effective_user.id
    print(user_id)
    wallets = await WalletService.get_wallet_by_user(user_id)

    kb = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_wallets")],
        [InlineKeyboardButton("🪙 SOL", callback_data="sol_wallets"), InlineKeyboardButton("💵 USDT", callback_data="usdt_wallets")],
        [InlineKeyboardButton("💼 Show Address", callback_data="show_address")],
        [InlineKeyboardButton("➕ Create Wallet", callback_data="create_wallet")],
        [InlineKeyboardButton("❌ Delete Wallet", callback_data="delete_wallet")],
    ]
    await update.message.reply_text(
        "Welcome to the Wallet Menu!",
        reply_markup=InlineKeyboardMarkup(kb),
    )
    return WALLET_MENU

async def wallet_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == "refresh_wallets":
        user_id = update.effective_user.id
        wallets = await WalletService.get_wallet_by_user(user_id)
        if wallets:
            msg = "🔄 Wallets refreshed:\n"
            for wallet in wallets:
                msg += f"- {wallet.public_key} ({'Deleted' if wallet.deleted else 'Active'})\n"
        else:
            msg = "❌ No wallets found."
        await query.edit_message_text(msg)

    elif choice == "sol_wallets":
        user_id = update.effective_user.id
        wallets = await WalletService.get_wallet_by_user(user_id)
        sol_wallets = [wallet for wallet in wallets if wallet.wallet_type == "SOL"]
        if sol_wallets:
            msg = "🪙 SOL Wallets:\n"
            for wallet in sol_wallets:
                balance = await WalletService.get_sol_balance(wallet.public_key)
                msg += f"- {wallet.public_key}\n  Balance: {balance} SOL\n"
        else:
            msg = "❌ No SOL wallets found."
        await query.edit_message_text(msg)

    elif choice == "usdt_wallets":
        user_id = update.effective_user.id
        wallets = await WalletService.get_wallet_by_user(user_id)
        usdt_wallets = [wallet for wallet in wallets if wallet.wallet_type == "USDT"]
        if usdt_wallets:
            msg = "💵 USDT Wallets:\n"
            for wallet in usdt_wallets:
                balance = await WalletService.get_usdt_balance(wallet.public_key)
                msg += f"- {wallet.public_key}\n  Balance: {balance} USDT\n"
        else:
            msg = "❌ No USDT wallets found."
        await query.edit_message_text(msg)

    elif choice == "show_address":
        user_id = update.effective_user.id
        wallets = await WalletService.get_wallet_by_user(user_id)
        if wallets:
            msg = "💼 Wallet Addresses:\n"
            for wallet in wallets:
                msg += f"- {wallet.public_key}\n"
        else:
            msg = "❌ No wallets found."
        await query.edit_message_text(msg)

    elif choice == "create_wallet":
        await query.edit_message_text("Enter the type of wallet (e.g., SOL or USDT):")
        return CREATE_WALLET

    elif choice == "delete_wallet":
        user_id = update.effective_user.id
        wallets = await WalletService.get_wallet_by_user(user_id)
        if wallets:
            kb = [
                [InlineKeyboardButton(f"❌ {wallet.public_key}", callback_data=f"delete_{wallet.id}")]
                for wallet in wallets
            ]
            kb.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")])
            await query.edit_message_text(
                "Select a wallet to delete:", reply_markup=InlineKeyboardMarkup(kb)
            )
        else:
            await query.edit_message_text("❌ No wallets found.")

    elif choice.startswith("delete_"):
        wallet_id = choice.replace("delete_", "")
        success = await WalletService.soft_delete_wallet(wallet_id)
        if success:
            await query.edit_message_text("✅ Wallet deleted successfully!")
        else:
            await query.edit_message_text("❌ Failed to delete wallet.")
        return WALLET_MENU

    elif choice == "back_to_menu":
        await wallet_command(update, context)
        return WALLET_MENU

async def create_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    wallet_type = update.message.text.strip()
    wallet = await WalletService.create_wallet(user_id, wallet_type)
    await update.message.reply_text(f"✅ Wallet created!\nPublic Key: {wallet.public_key}")
    return WALLET_MENU