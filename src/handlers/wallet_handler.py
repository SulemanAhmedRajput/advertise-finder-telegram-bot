from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from constant.language_constant import get_text
from constants import State
from helpers import get_sol_balance
from services.wallet_service import WalletService
from solders.pubkey import Pubkey
from utils.error_wrapper import catch_async
from utils.solana_config import solana_client
from telegram.ext import ContextTypes
from solders.token.associated import get_associated_token_address
from constant.language_constant import USDT_MINT_ADDRESS

# Define the USDT mint address


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
        message = "<b>Your SOL Wallets:</b>\n"
        for wallet in wallets:
            if wallet.wallet_type == "SOL":
                try:
                    balance = await get_sol_balance(wallet.public_key)
                    message += (
                        f"<b>Name:</b> {wallet.name}, <b>Balance:</b> {balance} SOL\n"
                    )
                except Exception as e:
                    message += f"<b>Name:</b> {wallet.name}, <b>Error:</b> {str(e)}\n"

    # Check if the update is from a callback query or a command
    if update.callback_query:
        await update.callback_query.message.edit_text(message, parse_mode="HTML")
    else:
        await update.message.reply_text(message, parse_mode="HTML")

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
                try:
                    # Get the associated token account for the wallet
                    token_account = get_associated_token_address(
                        Pubkey(wallet.public_key), Pubkey.from_string(USDT_MINT_ADDRESS)
                    )

                    # Fetch the USDT balance using get_token_account_balance
                    response = solana_client.get_token_account_balance(token_account)
                    if response.value:
                        balance = (
                            response.value.amount
                        )  # Balance in the smallest unit (e.g., lamports for SOL)
                        decimals = response.value.decimals  # Decimals for the token
                        # Convert balance to human-readable format
                        human_balance = int(balance) / (10**decimals)
                        message += (
                            f"Name: {wallet.name}, Balance: {human_balance} USDT\n"
                        )
                    else:
                        message += f"Name: {wallet.name}, Balance: 0 USDT\n"
                except Exception as e:
                    message += (
                        f"Name: {wallet.name}, Error fetching balance: {str(e)}\n"
                    )

    await update.callback_query.message.edit_text(message)
    return State.WALLET_MENU


@catch_async
async def show_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the public address of a wallet."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)

    if not wallets:
        message = "<b>You don't have any wallets yet. </b>"
    else:
        kb = [
            [
                InlineKeyboardButton(
                    wallet.name, callback_data=f"show_address_{wallet.id}"
                )
            ]
            for wallet in wallets
        ]
        message = "<b>Select a wallet to view its address: </b>"

    await update.callback_query.message.edit_text(
        message, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML"
    )
    return State.SHOW_ADDRESS


@catch_async
async def show_specific_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the specific wallet address."""
    query = update.callback_query
    wallet_id = query.data.split("_")[-1]
    wallet = await WalletService.get_wallet_by_id(wallet_id)

    if wallet:
        message = f"Wallet Name: {wallet.name} \n\n Public Address: {wallet.public_key}"
    else:
        message = "Wallet not found."

    await update.callback_query.message.edit_text(message)
    return State.WALLET_MENU


@catch_async
async def view_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View transaction history."""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    wallets = await WalletService.get_wallet_by_user(user_id)

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
    await update.callback_query.message.edit_text(
        message, reply_markup=InlineKeyboardMarkup(kb)
    )
    return State.VIEW_HISTORY


@catch_async
async def view_specific_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View the specific wallet's transaction history."""
    query = update.callback_query
    wallet_id = query.data.split("_")[-1]
    wallet = await WalletService.get_wallet_by_id(wallet_id)

    if wallet:
        history = await WalletService.get_usdt_history(wallet.public_key)
        message = f"Transaction History for {wallet.name}:\n"
        for tx in history:
            message += f"Signature: {tx['signature']}, Time: {tx['block_time']}\n"
    else:
        message = "Wallet not found."

    await update.callback_query.message.edit_text(message)
    return State.WALLET_MENU


@catch_async
async def create_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask the user to select the wallet type."""
    query = update.callback_query
    await query.answer()

    # Create buttons for wallet type selection
    keyboard = [
        [
            InlineKeyboardButton("USDT", callback_data="USDT"),
            InlineKeyboardButton("SOL", callback_data="SOL"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = "Please select the wallet type:"
    await query.edit_message_text(text=message, reply_markup=reply_markup)
    return State.SELECT_WALLET_TYPE


@catch_async
async def select_wallet_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the selected wallet type and ask for the wallet name."""
    query = update.callback_query
    await query.answer()

    # Store the selected wallet type in context
    context.user_data["wallet_type"] = query.data

    message = "Please enter the wallet name:"
    await query.edit_message_text(text=message)
    return State.ENTER_WALLET_NAME


@catch_async
async def process_create_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the wallet creation with the provided name and type."""
    wallet_name = update.message.text.strip()
    wallet_type = context.user_data.get("wallet_type")
    user_id = update.effective_user.id

    # Check if the wallet name is already used
    if await WalletService.check_wallet_name_used(user_id, wallet_name):
        message = (
            "A wallet with this name already exists. Please choose a different name."
        )
        await update.message.reply_text(message)
        return State.ENTER_WALLET_NAME

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
        await query.message.edit_text(message)
        return State.WALLET_MENU

    kb = [
        [
            InlineKeyboardButton(
                wallet.name, callback_data=f"confirm_delete_wallet_{wallet.id}"
            )
        ]
        for wallet in wallets
    ]

    message = "Select a wallet to delete:"
    await query.message.edit_text(message, reply_markup=InlineKeyboardMarkup(kb))
    return State.CONFIRM_DELETE_WALLET


@catch_async
async def confirm_delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask for confirmation before deleting the wallet."""
    query = update.callback_query
    wallet_id = query.data.split("_")[-1]

    kb = [
        [
            InlineKeyboardButton(
                "Yes, delete", callback_data=f"delete_wallet_{wallet_id}"
            ),
            InlineKeyboardButton("Cancel", callback_data="wallet_menu"),
        ]
    ]

    message = (
        "Are you sure you want to delete this wallet? This action cannot be undone."
    )
    await query.message.edit_text(message, reply_markup=InlineKeyboardMarkup(kb))
    return State.DELETE_WALLET


@catch_async
async def process_delete_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process the deletion of a wallet."""
    query = update.callback_query
    wallet_id = query.data.split("_")[-1]

    success = await WalletService.soft_delete_wallet(wallet_id)
    message = "Wallet deleted successfully." if success else "Failed to delete wallet."

    await query.message.edit_text(message)
    return State.WALLET_MENU
