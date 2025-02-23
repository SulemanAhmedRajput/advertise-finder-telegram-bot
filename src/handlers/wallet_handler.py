from typing import Optional, List
from constant.language_constant import get_text
from constants import State
from models.wallet_model import Wallet
from services.wallet_service import WalletService
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
)
from services.wallet_service import solana_client
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
        [
            InlineKeyboardButton(
                get_text(user_id, "refresh_btn"), callback_data="refresh_wallets"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "sol_btn"), callback_data="sol_wallets"
            ),
            InlineKeyboardButton(
                get_text(user_id, "usdt_btn"), callback_data="usdt_wallets"
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "address_btn"), callback_data="show_address"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "history_btn"), callback_data="view_history"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "create_wallet_btn"), callback_data="create_wallet"
            ),
            InlineKeyboardButton(
                get_text(user_id, "delete_wallet_btn"), callback_data="delete_wallet"
            ),
        ],
    ]

    if update.message:
        await update.message.reply_text(
            get_text(user_id, "welcome_text"), reply_markup=InlineKeyboardMarkup(kb)
        )
    elif update.callback_query:
        await update.callback_query.message.reply_text(
            get_text(user_id, "welcome_text"), reply_markup=InlineKeyboardMarkup(kb)
        )

    return State.WALLET_MENU


@catch_async
async def refresh_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Refresh the wallet list."""
    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)
    if wallets is None:
        wallets = []

    # Rebuild the keyboard with updated wallet information
    kb = [
        [
            InlineKeyboardButton(
                get_text(user_id, "refresh_btn"), callback_data="refresh_wallets"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "sol_btn"), callback_data="sol_wallets"
            ),
            InlineKeyboardButton(
                get_text(user_id, "usdt_btn"), callback_data="usdt_wallets"
            ),
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "address_btn"), callback_data="show_address"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "history_btn"), callback_data="view_history"
            )
        ],
        [
            InlineKeyboardButton(
                get_text(user_id, "create_wallet_btn"), callback_data="create_wallet"
            ),
            InlineKeyboardButton(
                get_text(user_id, "delete_wallet_btn"), callback_data="delete_wallet"
            ),
        ],
    ]

    await update.callback_query.message.edit_text(
        get_text(user_id, "refresh_wallet_text"), reply_markup=InlineKeyboardMarkup(kb)
    )
    return State.WALLET_MENU


@catch_async
async def sol_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display SOL wallet balances."""
    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)

    if not wallets:
        message = get_text(user_id, "no_wallet").format(
            {"wallet_name": "SOL"}
        )  # TODO: Must be check the condition
    else:
        # TODO: From there must be done when light has arrive
        message = "Your SOL Wallets:\n"
        for wallet in wallets:
            if wallet.wallet_type == "SOL":
                balance = (
                    solana_client.get_balance(
                        Pubkey.from_string(wallet.public_key)
                    ).value
                    / 1_000_000_000
                )
                message += f"Name: {wallet.name}, Balance: {balance} SOL\n"

    await update.callback_query.message.reply_text(message)
    return State.WALLET_MENU


@catch_async
async def usdt_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display USDT wallet balances."""
    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)

    if not wallets:
        message = "You don't have any USDT wallets yet."
    else:
        message = "Your USDT Wallets:\n"
        for wallet in wallets:
            if wallet.wallet_type == "USDT":
                balance = await WalletService.get_usdt_balance(wallet.public_key)
                message += f"Name: {wallet.name}, Balance: {balance} USDT\n"

    await update.callback_query.message.reply_text(message)
    return State.WALLET_MENU


@catch_async
async def show_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the public address of a wallet."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)

    if not wallets:
        message = "You don't have any wallets yet."
    else:
        kb = [
            [
                InlineKeyboardButton(
                    wallet.name, callback_data=f"show_address_{wallet.id}"
                )
            ]
            for wallet in wallets
        ]
        message = "Select a wallet to view its address:"

    await query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(kb))
    return State.SHOW_ADDRESS


@catch_async
async def show_specific_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the specific wallet address."""
    query = update.callback_query
    wallet_id = query.data.split("_")[-1]
    wallet = await Wallet.get(wallet_id)

    print("I am calling from the show_specific address")

    if wallet:
        message = f"Wallet Name: {wallet.name}\nPublic Address: {wallet.public_key}"
    else:
        message = "Wallet not found."

    await query.message.reply_text(message)
    return State.WALLET_MENU


@catch_async
async def view_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View transaction history."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)
    print(f"This is the wallet with the name {wallets}")

    if not wallets or wallets == []:
        message = "You don't have any wallets yet."
        kb = []  # Define an empty keyboard if there are no wallets
    else:
        kb = [
            [
                InlineKeyboardButton(
                    wallet.name, callback_data=f"view_history_{wallet.id}"
                )
            ]
            for wallet in wallets
        ]
        message = "Select a wallet to view its transaction history:"

    # Ensure `kb` is always defined before using it
    await query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(kb))
    return State.VIEW_HISTORY


@catch_async
async def view_specific_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the specific wallet's transaction history."""
    query = update.callback_query
    wallet_id = query.data.split("_")[-1]
    wallet = await Wallet.get(wallet_id)

    if wallet:
        history = await WalletService.get_usdt_history(wallet.public_key)
        message = f"Transaction History for {wallet.name}:\n"
        for tx in history:
            message += f"Signature: {tx['signature']}, Time: {tx['block_time']}\n"
    else:
        message = "Wallet not found."

    await query.message.reply_text(message)
    return State.WALLET_MENU


@catch_async
async def create_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a new wallet."""
    query = update.callback_query
    await query.answer()
    message = (
        "Enter the wallet name and type (e.g., 'MyWallet SOL' or 'MyWallet USDT'):"
    )
    await query.message.reply_text(message)
    return State.CREATE_WALLET


@catch_async
async def process_create_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the creation of a new wallet."""
    text = update.message.text.strip()

    # Validate the input format
    if " " not in text:
        message = "Invalid input format. Please enter the wallet name and type separated by a space (e.g., 'MyWallet SOL')."
        await update.message.reply_text(message)
        return State.CREATE_WALLET

    # Split the input into wallet name and type
    wallet_name, wallet_type = text.rsplit(maxsplit=1)
    user_id = update.effective_user.id

    # Check if the wallet name is already used
    if await WalletService.check_wallet_name_used(user_id, wallet_name):
        message = (
            "A wallet with this name already exists. Please choose a different name."
        )
    elif wallet_type not in ["SOL", "USDT"]:
        message = "Invalid wallet type. Please choose either 'SOL' or 'USDT'."
    else:
        # Create the wallet
        wallet = await WalletService.create_wallet(user_id, wallet_type, wallet_name)
        message = (
            f"Wallet created successfully!\n"
            f"Name: {wallet.name}\n"
            f"Type: {wallet.wallet_type}\n"
            f"Public Key: {wallet.public_key}"
        )

    await update.message.reply_text(message)
    return State.WALLET_MENU


@catch_async
async def delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a wallet."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)

    if not wallets:
        message = "You don't have any wallets to delete."
    else:
        kb = [
            [
                InlineKeyboardButton(
                    wallet.name, callback_data=f"delete_wallet_{wallet.id}"
                )
            ]
            for wallet in wallets
        ]
        message = "Select a wallet to delete:"

    await query.message.reply_text(message, reply_markup=InlineKeyboardMarkup(kb))
    return State.DELETE_WALLET


@catch_async
async def process_delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the deletion of a wallet."""
    query = update.callback_query
    wallet_id = query.data.split("_")[-1]

    success = await WalletService.soft_delete_wallet(wallet_id)
    if success:
        message = "Wallet deleted successfully."
    else:
        message = "Failed to delete wallet."

    await query.message.reply_text(message)
    return State.WALLET_MENU
