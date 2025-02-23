from typing import List, Optional
from beanie import PydanticObjectId
from models.wallet_model import Wallet  # Import your Wallet model
from solders.pubkey import Pubkey
from solana.rpc.api import Client
from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID

from utils.wallet import create_sol_wallet

# Initialize Solana client
SOLANA_NETWORK = "https://api.devnet.solana.com"
solana_client = Client(SOLANA_NETWORK)

# USDT Mint Address on Solana
USDT_MINT_ADDRESS = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"


class WalletService:
    @staticmethod
    async def create_wallet(user_id: str, wallet_type: str, wallet_name: str) -> Wallet:
        """
        Create a new wallet and save it to the database.
        :param user_id: The Telegram user ID.
        :param wallet_type: The type of wallet (e.g., "SOL" or "USDT").
        :return: The created Wallet object.
        """
        if wallet_type == "SOL":
            sol_wallet = create_sol_wallet(wallet_name)

            wallet = Wallet(
                public_key=sol_wallet["public_key"],
                private_key=sol_wallet["secret_key"],
                user_id=user_id,
                name=sol_wallet["name"],
                wallet_type="SOL",
                deleted=False,
            )
            await wallet.insert()

        return wallet

    @staticmethod
    async def soft_delete_wallet(wallet_id: PydanticObjectId) -> bool:
        """
        Soft delete a wallet by setting the `deleted` flag to True.
        :param wallet_id: The ID of the wallet to soft delete.
        :return: True if the wallet was soft-deleted successfully, False otherwise.
        """
        wallet = await Wallet.get(wallet_id)
        if not wallet:
            return False
        wallet.deleted = True
        await wallet.save()
        return True

    @staticmethod
    async def get_wallet_by_user(
        user_id: int, include_deleted: bool = False
    ) -> List[Wallet]:
        """
        Retrieve all wallets associated with a user.
        :param user_id: The Telegram user ID.
        :param include_deleted: Whether to include soft-deleted wallets.
        :return: A list of Wallet objects.
        """
        query = Wallet.find(Wallet.user_id == user_id)
        if not include_deleted:
            query = query.find(Wallet.deleted == False)
        wallets = await query.to_list()
        return wallets

    @staticmethod
    async def get_usdt_balance(public_key: str) -> float:
        """
        Retrieve the USDT balance for a wallet.
        :param public_key: The public key of the wallet.
        :return: The USDT balance as a float.
        """
        try:
            pubkey = Pubkey.from_string(public_key)
            usdt_mint = Pubkey.from_string(USDT_MINT_ADDRESS)

            # Fetch the associated token account for USDT
            response = solana_client.get_token_accounts_by_owner(
                pubkey, {"mint": usdt_mint}
            )
            if not response.value:
                return 0.0  # No USDT token account found

            # Extract the token account info
            token_account_info = response.value[0].account.data.parsed["info"]
            balance = token_account_info["tokenAmount"]["uiAmount"]
            return float(balance)
        except Exception as e:
            print(f"Error fetching USDT balance: {e}")
            return 0.0

    @staticmethod
    async def get_usdt_history(public_key: str) -> List[dict]:
        """
        Retrieve the USDT transaction history for a wallet.
        :param public_key: The public key of the wallet.
        :return: A list of transaction details.
        """
        try:
            pubkey = Pubkey.from_string(public_key)
            usdt_mint = Pubkey.from_string(USDT_MINT_ADDRESS)

            # Fetch all transactions involving the USDT mint
            response = solana_client.get_signatures_for_address(usdt_mint)
            signatures = [sig.signature for sig in response.value]

            transactions = []
            for signature in signatures:
                tx_response = solana_client.get_transaction(signature)
                if tx_response.value:
                    tx = tx_response.value
                    transactions.append(
                        {
                            "signature": str(tx.transaction.signatures[0]),
                            "block_time": tx.block_time,
                            "meta": tx.meta,
                        }
                    )
            return transactions
        except Exception as e:
            print(f"Error fetching USDT history: {e}")
            return []

    @staticmethod
    async def transfer_usdt(
        sender_private_key: str,
        recipient_public_key: str,
        amount: float,
    ) -> str:
        """
        Transfer USDT from one wallet to another.
        :param sender_private_key: The private key of the sender's wallet.
        :param recipient_public_key: The public key of the recipient's wallet.
        :param amount: The amount of USDT to transfer.
        :return: The transaction signature if successful, or an error message.
        """
        try:
            from solders.keypair import Keypair

            sender_keypair = Keypair.from_secret_key(bytes.fromhex(sender_private_key))
            sender_pubkey = sender_keypair.pubkey()

            # Initialize the USDT token client
            usdt_mint = Pubkey.from_string(USDT_MINT_ADDRESS)
            token_client = Token(
                solana_client, usdt_mint, TOKEN_PROGRAM_ID, sender_keypair
            )

            # Get the sender's associated token account
            sender_token_account = token_client.get_accounts(sender_pubkey)[0].address

            # Get or create the recipient's associated token account
            recipient_pubkey = Pubkey.from_string(recipient_public_key)
            recipient_token_account = token_client.create_associated_token_account(
                recipient_pubkey
            )

            # Transfer USDT
            tx_sig = token_client.transfer(
                source=sender_token_account,
                dest=recipient_token_account,
                owner=sender_pubkey,
                amount=int(
                    amount * 1_000_000
                ),  # Convert to lamports (USDT has 6 decimals)
            )
            return str(tx_sig)
        except Exception as e:
            print(f"Error transferring USDT: {e}")
            return f"❌ Error: {str(e)}"

    @staticmethod
    async def check_wallet_name_used(user_id: int, wallet_name: str) -> bool:
        # Query the database to check if there's a wallet with the same user_id and name
        wallet = await Wallet.find_one(
            Wallet.user_id == user_id, Wallet.name == wallet_name
        )
        return wallet is not None

    @staticmethod
    async def get_wallet_by_name(user_id: int, wallet_name: str) -> dict:
        """
        Retrieve a wallet by name.
        :param user_id: The Telegram user ID.
        :param wallet_name: The name of the wallet.
        :return: The wallet details as a dictionary.
        """
        wallet = await Wallet.find_one(
            Wallet.user_id == user_id, Wallet.name == wallet_name
        )
        if wallet:
            return wallet.model_dump()
        else:
            return None

    async def get_wallet_by_id(id: PydanticObjectId) -> dict:
        """
        Retrieve a wallet by ID.
        :param id: The ID of the wallet.
        :return: The wallet details as a dictionary.
        """
        wallet = await Wallet.get(id)
        if wallet:
            return wallet.model_dump()
        else:
            return None
