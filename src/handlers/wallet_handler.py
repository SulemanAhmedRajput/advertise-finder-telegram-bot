from typing import Optional, List
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
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from constants import CREATE_WALLET, END, HISTORY_MENU, NAME_WALLET, WALLET_MENU, get_text, user_data_store
from utils.error_wrapper import catch_async
from utils.wallet import delete_user_wallet, load_user_wallet, client, Pubkey



@catch_async
async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point for /wallet command."""
    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)
    if wallets is None:
        wallets = []

    kb = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_wallets")],
        [InlineKeyboardButton("🪙 SOL", callback_data="sol_wallets"),
         InlineKeyboardButton("💵 USDT", callback_data="usdt_wallets")],
        [InlineKeyboardButton("💼 Show Address", callback_data="show_address")],
        [InlineKeyboardButton("📜 History", callback_data="view_history")],  # Button for transaction history
        [InlineKeyboardButton("➕ Create Wallet", callback_data="create_wallet"), InlineKeyboardButton("❌ Delete Wallet", callback_data="delete_wallet")],  # This button triggers the creation
    ]

    message = "Welcome to the Wallet Menu!"
    
    if update.message:
        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(kb))
    elif update.callback_query:
        await update.callback_query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(kb))
    
    return WALLET_MENU


@catch_async
async def select_wallet_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show buttons for selecting wallet type (SOL / USDT)."""
    print("Inside the select wallet type handler")
    keyboard = [
        [InlineKeyboardButton("🪙 SOL", callback_data="sol_wallet_type")],
        [InlineKeyboardButton("💵 USDT", callback_data="usdt_wallet_type")],
    ]
    
    if update.message:
        await update.message.reply_text(
            "Please choose the type of wallet you want to create:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            "Please choose the type of wallet you want to create:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    return CREATE_WALLET  # Proceed to ask for the wallet name


@catch_async
async def create_wallet_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store selected wallet type and ask for wallet name."""
    wallet_type = update.callback_query.data.split("_")[0].upper()

    # Store wallet type in context.user_data
    context.user_data['wallet_type'] = wallet_type

    # Acknowledge the wallet type selection and ask for the wallet name
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        f"✅ Wallet type '{wallet_type}' selected. Please provide a name for your wallet."
    )

    return CREATE_WALLET  # Continue to next step for wallet name


@catch_async
async def create_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Safely handle wallet creation."""
    wallet_type = context.user_data.get('wallet_type')
    if not wallet_type:
        await update.message.reply_text("⚠️ Please select a wallet type first.")
        return WALLET_MENU
    
    wallet_name = update.message.text.strip()
    user_id = update.effective_user.id

    # Create the wallet using the selected type and provided name
    wallet = await WalletService.create_wallet(user_id, wallet_type, wallet_name)
    await update.message.reply_text(f"✅ {wallet_type} wallet created!\n🔑 Address: `{wallet.public_key}`", parse_mode="Markdown")


    return END


@catch_async
async def refresh_wallets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Safely refresh the wallet list."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id) or []

    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_wallets")],
                [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]

    for wallet in wallets:
        keyboard.insert(1, [InlineKeyboardButton(f"{wallet.wallet_type} - {wallet.public_key}", 
                                                 callback_data=f"show_address_{wallet.public_key}")])

    new_message = "Here are your wallets:"
    new_reply_markup = InlineKeyboardMarkup(keyboard)

    # Check if the message content or reply markup has changed
    current_message = query.message.text
    current_reply_markup = query.message.reply_markup

    if current_message != new_message or current_reply_markup != new_reply_markup:
        await query.edit_message_text(new_message, reply_markup=new_reply_markup)
    else:
        await query.answer("No changes to the wallet list.")

    return WALLET_MENU


@catch_async
async def show_wallets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_type: str) -> int:
    """Generic handler for SOL and USDT wallets."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]

    if wallets:
        for wallet in wallets:
            keyboard.insert(0, [InlineKeyboardButton(f"{wallet.name} - ({wallet.public_key[:6]}...)", 
                                                     callback_data=f"show_address_{wallet.public_key}")])
        message = f"Your {wallet_type} wallets:"
    else:
        message = f"No {wallet_type} wallets found."

    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return WALLET_MENU

@catch_async
async def show_address_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Safely show wallet address and balance."""
    query = update.callback_query
    await query.answer()
    public_key = query.data.split("_")[-1]
    response = await client.get_balance(Pubkey(public_key))
    balance = response['result']['value'] / 1e9  # Convert lamports to SOL
    await client.close()
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
    await query.edit_message_text(
        f"🔑 Wallet Address:\n`{public_key}`\n💰 Balance: {balance} SOL",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return WALLET_MENU
    


@catch_async
async def delete_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display a list of wallets with delete buttons."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id) or []

    if not wallets:
        await query.edit_message_text("No wallets found to delete.", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
        ]))
        return WALLET_MENU

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
    for wallet in wallets:
        keyboard.insert(0, [InlineKeyboardButton(f"Delete {wallet.wallet_type} - {wallet.public_key[:6]}...", 
                                                 callback_data=f"confirm_delete_{wallet.id}")])

    await query.edit_message_text("Select a wallet to delete:", reply_markup=InlineKeyboardMarkup(keyboard))
    return WALLET_MENU

@catch_async
async def view_transaction_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Fetch and display the transaction history for a selected wallet."""
    query = update.callback_query
    await query.answer()

    public_key = query.data.split("_")[-1]
    transactions = await WalletService.get_usdt_history(public_key)

    if transactions:
        message = "📜 *Transaction History:*\n\n"
        for tx in transactions[:5]:  # Limit to the latest 5 transactions
            message += f"🔹 Tx: [{tx['signature']}](https://solscan.io/tx/{tx['signature']}?cluster=devnet)\n"
            message += f"📅 Time: {tx['block_time']}\n"
            message += f"🔍 Meta: {tx['meta']}\n\n"
    else:
        message = "⚠️ No transaction history found for this wallet."

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="Markdown")
    return HISTORY_MENU



@catch_async
async def confirm_delete_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask for confirmation before deleting the wallet."""
    query = update.callback_query
    await query.answer()

    wallet_id = query.data.split("_")[-1]
    context.user_data['wallet_id_to_delete'] = wallet_id

    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="delete_wallet_confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="delete_wallet_cancel")],
    ]
    await query.edit_message_text(
        "Are you sure you want to delete this wallet?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return WALLET_MENU
@catch_async
async def cancel_delete_wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle wallet deletion cancellation."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Wallet deletion cancelled.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
    ]))
    return WALLET_MENU


@catch_async
async def delete_wallet_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle wallet deletion confirmation."""
    query = update.callback_query
    await query.answer()

    wallet_id = context.user_data.get('wallet_id_to_delete')
    if not wallet_id:
        await query.edit_message_text("⚠️ No wallet selected for deletion.")
        return WALLET_MENU

    success = await WalletService.soft_delete_wallet(wallet_id)
    message = "✅ Wallet deleted successfully." if success else "❌ Failed to delete wallet. It may not exist."

    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
    await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
    return WALLET_MENU


@catch_async
async def delete_wallet_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle wallet deletion cancellation."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text("Wallet deletion cancelled.", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]
    ]))
    return WALLET_MENU