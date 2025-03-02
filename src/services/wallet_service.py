from typing import Any, Dict, List, Optional
from beanie import PydanticObjectId
from solders.pubkey import Pubkey
from spl.token.client import Token
from spl.token.constants import TOKEN_PROGRAM_ID
from constant.language_constant import USDT_MINT_ADDRESS
from models.wallet_model import Wallet
from utils.error_wrapper import catch_async
from utils.wallet import create_sol_wallet, create_usdt_wallet
from utils.solana_config import solana_client
from solana.rpc.api import Client
from solders.system_program import transfer, TransferParams
from solders.transaction import Transaction
from solders.message import Message
from solders.keypair import Keypair


class WalletService:
    @staticmethod
    async def create_wallet(user_id: str, wallet_type: str, wallet_name: str) -> Wallet:
        """
        Create a new wallet and save it to the database.
        :param user_id: The Telegram user ID.
        :param wallet_type: The type of wallet (e.g., "SOL" or "USDT").
        :param wallet_name: The name of the wallet.
        :return: The created Wallet object.
        """
        try:
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
            elif wallet_type == "USDT":
                usdt_wallet = create_usdt_wallet(wallet_name)
                wallet = Wallet(
                    public_key=usdt_wallet["public_key"],
                    private_key=usdt_wallet["secret_key"],
                    user_id=user_id,
                    name=usdt_wallet["name"],
                    wallet_type="USDT",
                    deleted=False,
                )
            else:
                raise ValueError("Unsupported wallet type.")

            await wallet.insert()
            return wallet
        except Exception as e:
            print(f"Error creating wallet: {e}")
            return None

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
        return await query.to_list()

    @staticmethod
    async def get_wallet_by_type(user_id: int, wallet_type: str) -> List[Wallet]:
        print(f"Getting wallets by type: {wallet_type}")
        return await Wallet.find(
            Wallet.user_id == user_id, Wallet.wallet_type == wallet_type
        ).to_list()

    @staticmethod
    async def get_usdt_balance(wallet_pubkey):
        token_client = Token(
            conn=solana_client,
            pubkey=Pubkey.from_string(USDT_MINT_ADDRESS),
            program_id=TOKEN_PROGRAM_ID,
            payer=wallet_pubkey,
        )

        balance = token_client.get_balance(wallet_pubkey)
        return balance

    @staticmethod  # TODO: Check if this works
    async def get_sol_balance(public_key: str) -> float:
        """
        Retrieve the SOL balance for a wallet.
        :param public_key: The public key of the wallet.
        :return: The SOL balance as a float.
        """
        try:
            publickey = Pubkey.from_string(public_key)
            balance = solana_client.get_balance(publickey)  # Await the async function
            print(f"Balance: {balance}")
            return balance / 1e9  # Convert lamports to SOL
        except Exception as e:
            print(f"Error fetching SOL balance: {e}")
            return 0.0

    @staticmethod
    async def get_wallet_by_id(id: PydanticObjectId) -> dict:
        """
        Retrieve a wallet by ID.
        :param id: The ID of the wallet.
        :return: The wallet details as a dictionary.
        """
        wallet = await Wallet.get(id)
        return wallet.model_dump() if wallet else None

    @staticmethod
    async def transfer_funds(
        wallet_type: str,
        sender_private_key: str,
        recipient_public_key: str,
        amount: float,
    ) -> str:
        """
        Generalized method to transfer funds, supports both SOL and USDT.
        :param wallet_type: The type of wallet (e.g., "SOL" or "USDT").
        :param sender_private_key: The sender's private key.
        :param recipient_public_key: The recipient's public key.
        :param amount: The amount to transfer.
        :return: Transaction signature if successful, or an error message.
        """
        try:

            sender_keypair = Keypair.from_secret_key(bytes.fromhex(sender_private_key))
            sender_pubkey = sender_keypair.pubkey()

            if wallet_type == "SOL":
                return await WalletService.transfer_sol(
                    sender_keypair, recipient_public_key, amount
                )
            elif wallet_type == "USDT":
                return await WalletService.transfer_usdt(
                    sender_private_key, recipient_public_key, amount
                )
            else:
                return "Invalid wallet type."
        except Exception as e:
            print(f"Error transferring {wallet_type}: {e}")
            return f"❌ Error: {e}"

    @staticmethod
    async def transfer_usdt(
        sender_private_key: str, recipient_public_key: str, amount: float
    ) -> str:
        """
        Transfer USDT from one wallet to another.
        :param sender_private_key: The private key of the sender's wallet.
        :param recipient_public_key: The public key of the recipient's wallet.
        :param amount: The amount to transfer.
        :return: The transaction signature if successful.
        """
        try:
            sender_keypair = Keypair.from_secret_key(bytes.fromhex(sender_private_key))
            sender_pubkey = sender_keypair.pubkey()
            usdt_mint = Pubkey.from_string(USDT_MINT_ADDRESS)
            token_client = Token(
                solana_client, usdt_mint, TOKEN_PROGRAM_ID, sender_keypair
            )

            sender_token_account = token_client.get_accounts(sender_pubkey)[0].address
            recipient_token_account = token_client.create_associated_token_account(
                Pubkey.from_string(recipient_public_key)
            )

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
    async def confirm_transaction(transaction_signature: str) -> dict:
        """
        Confirm a transaction's status on the Solana blockchain.
        :param transaction_signature: The signature of the transaction to confirm.
        :return: A dictionary with the transaction status.
        """
        try:
            response = solana_client.get_confirmed_transaction(transaction_signature)
            if response["result"] is None:
                return {"status": "error", "message": "Transaction not confirmed"}

            status = response["result"]["meta"]["status"]
            if status["Ok"]:
                return {"status": "success", "message": "Transaction confirmed"}
            else:
                return {"status": "error", "message": "Transaction failed"}
        except Exception as e:
            print(f"Error confirming transaction: {e}")
            return {"status": "error", "message": f"❌ Error: {str(e)}"}

    @staticmethod
    async def refresh_wallet(wallet_type: str, user_id: int):
        """
        Refresh a wallet's balance for SOL or USDT.
        :param wallet_type: The type of wallet to refresh ("SOL" or "USDT").
        :param user_id: The user_id to identify the wallet.
        :return: A dictionary containing the wallet's balance information.
        """
        try:
            wallets = await WalletService.get_wallet_by_user(user_id)
            wallet = next((w for w in wallets if w.wallet_type == wallet_type), None)

            if not wallet:
                return {"status": "error", "message": "Wallet not found"}

            if wallet_type == "SOL":
                balance = await WalletService.get_sol_balance(wallet.public_key)
                return {"status": "success", "balance": balance}
            elif wallet_type == "USDT":
                balance = await WalletService.get_usdt_balance(wallet.public_key)
                return {"status": "success", "balance": balance}
            else:
                return {"status": "error", "message": "Invalid wallet type"}

        except Exception as e:
            print(f"Error refreshing wallet: {e}")
            return {"status": "error", "message": f"❌ Error: {str(e)}"}

    @staticmethod
    async def wallet_exists(public_key: str) -> bool:
        """
        Check if a wallet exists by its public key.
        :param public_key: The public key of the wallet.
        :return: True if the wallet exists, False otherwise.
        """
        try:
            wallet = await Wallet.find_one(Wallet.public_key == public_key)
            return wallet is not None
        except Exception as e:
            print(f"Error checking wallet existence: {e}")
            return False

    @staticmethod
    async def get_wallet_balance(public_key: str, wallet_type: str) -> dict:
        """
        Get the balance of a wallet (SOL or USDT) based on the public key.
        :param public_key: The wallet's public key.
        :param wallet_type: The type of wallet (SOL or USDT).
        :return: A dictionary with the wallet's balance.
        """
        try:
            if wallet_type == "SOL":
                balance = await solana_client.get_balance(Pubkey(public_key))
                return {"status": "success", "balance": balance["result"]["value"]}
            elif wallet_type == "USDT":
                token_account = await solana_client.get_token_account_balance(
                    Pubkey(public_key), mint=Pubkey(USDT_MINT_ADDRESS)
                )
                return {
                    "status": "success",
                    "balance": token_account["result"]["value"]["uiAmount"],
                }
            else:
                return {"status": "error", "message": "Invalid wallet type"}
        except Exception as e:
            print(f"Error fetching wallet balance: {e}")
            return {"status": "error", "message": f"❌ Error: {str(e)}"}

    @staticmethod
    @catch_async
    def send_sol(
        self, sender_private_key: str, recipient_address: str, amount_sol: float
    ):
        """
        Send SOL from the sender to the recipient.

        :param sender_private_key: The private key of the sender (Base58 encoded).
        :param recipient_address: The public key of the recipient.
        :param amount_sol: The amount of SOL to send.
        :return: Transaction signature.
        """
        try:
            # Convert SOL to lamports (1 SOL = 1,000,000,000 lamports)
            lamports = int(amount_sol * 1_000_000_000)

            # Load sender keypair
            sender = Keypair.from_base58_string(sender_private_key)

            # Load recipient public key
            recipient = Pubkey.from_string(recipient_address)

            # Create transfer instruction
            instruction = transfer(
                TransferParams(
                    from_pubkey=sender.pubkey(),
                    to_pubkey=recipient,
                    lamports=lamports,
                )
            )

            # Get latest blockhash
            blockhash_response = solana_client.get_latest_blockhash()
            recent_blockhash = blockhash_response.value.blockhash

            # Create message and transaction
            message = Message(instructions=[instruction], payer=sender.pubkey())
            transaction = Transaction(
                from_keypairs=[sender],
                message=message,
                recent_blockhash=recent_blockhash,
            )

            # Sign transaction
            transaction.sign([sender], recent_blockhash=recent_blockhash)

            # Send transaction
            send_response = self.client.send_transaction(transaction)

            return f"Transaction sent! Signature: {send_response.value}"

        except Exception as e:
            return f"Error: {str(e)}"

    @staticmethod
    async def check_wallet_name_used(user_id: int, wallet_name: str) -> bool:
        """
        Check if a wallet name is already used by a specific user.
        :param user_id: The Telegram user ID.
        :param wallet_name: The name of the wallet to check.
        :return: True if the name is already used, False otherwise.
        """
        wallet = await Wallet.find_one(
            Wallet.user_id == user_id, Wallet.name == wallet_name
        )
        return wallet is not None
