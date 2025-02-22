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
                get_text("refresh_btn"), callback_data="refresh_wallets"
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
                get_text("refresh_btn"), callback_data="refresh_wallets"
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


# @catch_async
# async def select_wallet_type_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Show buttons for selecting wallet type (SOL / USDT)."""
#     print("Inside the select wallet type handler")
#     user_id = update.effective_user.id
#     keyboard = [
#         [
#             InlineKeyboardButton(
#                 get_text(user_id, "sol_wallet"), callback_data="sol_wallet_type"
#             ),
#             InlineKeyboardButton(
#                 get_text(user_id, "usdt_wallet"), callback_data="usdt_wallet_type"
#             ),
#         ],
#     ]

#     if update.message:
#         await update.message.reply_text(
#             "Please choose the type of wallet you want to create:",
#             reply_markup=InlineKeyboardMarkup(keyboard),
#         )
#     elif update.callback_query:
#         await update.callback_query.message.reply_text(
#             "Please choose the type of wallet you want to create:",
#             reply_markup=InlineKeyboardMarkup(keyboard),
#         )

#     return State.CREATE_WALLET  # Proceed to ask for the wallet name


# @catch_async
# async def create_wallet_type_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Store selected wallet type and ask for wallet name."""
#     wallet_type = update.callback_query.data.split("_")[0].upper()

#     # Store wallet type in context.user_data
#     context.user_data["wallet_type"] = wallet_type

#     # Acknowledge the wallet type selection and ask for the wallet name
#     await update.callback_query.answer()
#     await update.callback_query.message.reply_text(
#         f"✅ Wallet type '{wallet_type}' selected. Please provide a name for your wallet."
#     )

#     return State.CREATE_WALLET  # Continue to next step for wallet name


# @catch_async
# async def create_wallet_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Safely handle wallet creation."""
#     wallet_type = context.user_data.get("wallet_type")
#     if not wallet_type:
#         await update.message.reply_text("⚠️ Please select a wallet type first.")
#         return State.WALLET_MENU

#     wallet_name = update.message.text.strip()
#     user_id = update.effective_user.id

#     # Create the wallet using the selected type and provided name
#     keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
#     wallet = await WalletService.create_wallet(user_id, wallet_type, wallet_name)
#     await update.message.reply_text(
#         f"✅ {wallet_type} wallet created!\n🔑 Address: {wallet.public_key}",
#         reply_markup=InlineKeyboardMarkup(keyboard),
#     )

#     return State.END


# @catch_async
# async def refresh_wallets_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Safely refresh the wallet list."""
#     query = update.callback_query
#     await query.answer()

#     user_id = update.effective_user.id
#     wallets = await WalletService.get_wallet_by_user(user_id) or []

#     keyboard = [
#         [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_wallets")],
#         [InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")],
#     ]

#     for wallet in wallets:
#         keyboard.insert(
#             1,
#             [
#                 InlineKeyboardButton(
#                     f"{wallet.wallet_type} - {wallet.public_key}",
#                     callback_data=f"show_address_{wallet.public_key}",
#                 )
#             ],
#         )

#     new_message = "Here are your wallets:"
#     new_reply_markup = InlineKeyboardMarkup(keyboard)

#     # Check if the message content or reply markup has changed
#     current_message = query.message.text
#     current_reply_markup = query.message.reply_markup

#     if current_message != new_message or current_reply_markup != new_reply_markup:
#         await query.edit_message_text(new_message, reply_markup=new_reply_markup)
#     else:
#         await query.answer("No changes to the wallet list.")

#     return State.WALLET_MENU


# @catch_async
# async def show_wallets_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE, wallet_type: str
# ) -> int:
#     """Generic handler for SOL and USDT wallets."""
#     query = update.callback_query
#     await query.answer()

#     user_id = update.effective_user.id
#     wallets = await WalletService.get_wallet_by_user(user_id)

#     keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]

#     if wallets:
#         for wallet in wallets:
#             keyboard.insert(
#                 0,
#                 [
#                     InlineKeyboardButton(
#                         f"{wallet.name} - ({wallet.public_key[:6]}...)",
#                         callback_data=f"show_address_{wallet.public_key}",
#                     )
#                 ],
#             )
#         message = f"Your {wallet_type} wallets:"
#     else:
#         message = f"No {wallet_type} wallets found."

#     await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
#     return State.WALLET_MENU


# @catch_async
# async def show_address_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Safely show wallet address and balance."""
#     query = update.callback_query
#     await query.answer()
#     public_key = query.data.split("_")[-1]
#     response = await client.get_balance(Pubkey(public_key))
#     balance = response["result"]["value"] / 1e9  # Convert lamports to SOL
#     await client.close()
#     keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
#     await query.edit_message_text(
#         f"🔑 Wallet Address:\n`{public_key}`\n💰 Balance: {balance} SOL",
#         reply_markup=InlineKeyboardMarkup(keyboard),
#         parse_mode="Markdown",
#     )
#     return State.WALLET_MENU


# @catch_async
# async def delete_wallet_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Display a list of wallets with delete buttons."""
#     query = update.callback_query
#     await query.answer()

#     user_id = update.effective_user.id
#     wallets = await WalletService.get_wallet_by_user(user_id) or []

#     if not wallets:
#         await query.edit_message_text(
#             "No wallets found to delete.",
#             reply_markup=InlineKeyboardMarkup(
#                 [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
#             ),
#         )
#         return State.WALLET_MENU

#     keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
#     for wallet in wallets:
#         keyboard.insert(
#             0,
#             [
#                 InlineKeyboardButton(
#                     f"{wallet.name} ({wallet.wallet_type}) - {wallet.public_key}",
#                     callback_data=f"confirm_delete_{wallet.id}",
#                 )
#             ],
#         )

#     await query.edit_message_text(
#         "Select a wallet to delete:", reply_markup=InlineKeyboardMarkup(keyboard)
#     )
#     return State.WALLET_MENU


# @catch_async
# async def view_transaction_history_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Fetch and display the transaction history for a selected wallet."""
#     query = update.callback_query
#     await query.answer()

#     public_key = query.data.split("_")[-1]
#     transactions = await WalletService.get_usdt_history(public_key)

#     if transactions:
#         message = "📜 *Transaction History:*\n\n"
#         for tx in transactions[:5]:  # Limit to the latest 5 transactions
#             message += f"🔹 Tx: [{tx['signature']}](https://solscan.io/tx/{tx['signature']}?cluster=devnet)\n"
#             message += f"📅 Time: {tx['block_time']}\n"
#             message += f"🔍 Meta: {tx['meta']}\n\n"
#     else:
#         message = "⚠️ No transaction history found for this wallet."

#     keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
#     reply_markup = InlineKeyboardMarkup(keyboard)

#     await query.edit_message_text(
#         message, reply_markup=reply_markup, parse_mode="Markdown"
#     )
#     return State.HISTORY_MENU


# @catch_async
# async def confirm_delete_wallet_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Ask for confirmation before deleting the wallet."""
#     query = update.callback_query
#     await query.answer()

#     wallet_id = query.data.split("_")[-1]
#     context.user_data["wallet_id_to_delete"] = wallet_id

#     keyboard = [
#         [InlineKeyboardButton("✅ Confirm", callback_data="delete_wallet_confirm")],
#         [InlineKeyboardButton("❌ Cancel", callback_data="delete_wallet_cancel")],
#     ]
#     await query.edit_message_text(
#         "Are you sure you want to delete this wallet?",
#         reply_markup=InlineKeyboardMarkup(keyboard),
#     )
#     return State.WALLET_MENU


# @catch_async
# async def cancel_delete_wallet_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Handle wallet deletion cancellation."""
#     query = update.callback_query
#     await query.answer()

#     await query.edit_message_text(
#         "Wallet deletion cancelled.",
#         reply_markup=InlineKeyboardMarkup(
#             [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
#         ),
#     )
#     return State.WALLET_MENU


# @catch_async
# async def delete_wallet_confirm_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Handle wallet deletion confirmation."""
#     query = update.callback_query
#     await query.answer()

#     wallet_id = context.user_data.get("wallet_id_to_delete")
#     if not wallet_id:
#         await query.edit_message_text("⚠️ No wallet selected for deletion.")
#         return State.WALLET_MENU

#     success = await WalletService.soft_delete_wallet(wallet_id)
#     message = (
#         "✅ Wallet deleted successfully."
#         if success
#         else "❌ Failed to delete wallet. It may not exist."
#     )

#     keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
#     await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
#     return State.WALLET_MENU


# @catch_async
# async def delete_wallet_cancel_handler(
#     update: Update, context: ContextTypes.DEFAULT_TYPE
# ) -> int:
#     """Handle wallet deletion cancellation."""
#     query = update.callback_query
#     await query.answer()

#     await query.edit_message_text(
#         "Wallet deletion cancelled.",
#         reply_markup=InlineKeyboardMarkup(
#             [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
#         ),
#     )
#     return State.WALLET_MENU
