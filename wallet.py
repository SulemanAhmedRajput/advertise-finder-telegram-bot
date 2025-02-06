import os
import json
import base58
from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from telegram import Update
from constants import CREATE_CASE_SUBMIT, WALLETS_DIR, user_data_store, get_text
from solders.transaction import Transaction
from solders.system_program import transfer
from solders.signature import Signature
from solana.rpc.types import TxOpts
from telegram.ext import (
    ContextTypes,
)

# Initialize Solana client
SOLANA_NETWORK = "https://api.devnet.solana.com"
client = Client(SOLANA_NETWORK)


async def transfer_solana_funds(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    from_wallet: dict,
    to_pubkey: str,
    amount: float,
):
    """Transfer funds from one wallet to another."""
    user_id = update.effective_user.id

    try:
        from_keypair = Keypair.from_secret_key(bytes.fromhex(from_wallet["secret_key"]))
        to_pubkey = Pubkey.from_string(to_pubkey)

        # Create the transaction
        transaction = Transaction().add(
            transfer(
                from_pubkey=from_keypair.pubkey(),
                to_pubkey=to_pubkey,
                lamports=int(amount * 1e9),  # Convert SOL to lamports
            )
        )

        # Send the transaction
        response = client.send_transaction(
            transaction, from_keypair, opts=TxOpts(skip_preflight=True)
        )

        if response["result"]:
            await update.message.reply_text(get_text(user_id, "transfer_success"))
        else:
            await update.message.reply_text(get_text(user_id, "transfer_failed"))
    except Exception as e:
        await update.message.reply_text(f"{get_text(user_id, 'transfer_error')}: {e}")


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
        print(f"Error creating wallet: {e}")
        return None


def load_user_wallet(user_id: int):
    """Load wallet info from user_data_store or from file if needed."""
    wallet_data = user_data_store.get(user_id, {}).get("wallet")
    if wallet_data:
        return wallet_data
    return None


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
