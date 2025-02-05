import os
import json
import base58
from solders.keypair import Keypair
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from constants import WALLETS_DIR, user_data_store, get_text

# Initialize Solana client
try:
    SOLANA_NETWORK = "https://api.devnet.solana.com"
    client = Client(SOLANA_NETWORK)
except ImportError:
    client = None


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
