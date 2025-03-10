from tronpy import Tron
from tronpy.keys import PrivateKey
from tronpy.contract import Contract

class TronWallet:
    """
    Service for managing TRON wallets and transactions, including USDT (TRC20) operations.
    """

    # USDT TRC20 Contract Address (Mainnet)
    USDT_CONTRACT = "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"

    # Initialize Tron Client
    client = Tron(network="mainnet")  # Use "shasta" for testnet

    @staticmethod
    def create_wallet(wallet_name):
        """
        Creates a new TRON Wallet and returns its details.
        """
        private_key = PrivateKey.random()
        address = private_key.public_key.to_base58check_address()

        return {
            "private_key": private_key.hex(),  # Keep this secret!
            "public_key": address,
            "name": wallet_name
            
        }

    @staticmethod
    def get_trx_balance(address):
        """
        Fetches the TRX balance of a TRON wallet.
        """
        try:
            return TronWallet.client.get_account_balance(address)  # Balance is in TRX
        except Exception:
            return 0  # Wallet may be new and unfunded

    @staticmethod
    def get_usdt_balance(address):
        """
        Fetches the USDT (TRC20) balance of a TRON wallet.
        """
        try:
            # Load contract with ABI
            contract = TronWallet.client.get_contract(TronWallet.USDT_CONTRACT).with_abi([
                {
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "payable": False,
                    "stateMutability": "View",
                    "type": "Function",
                }
            ])
            
            # Call balanceOf function
            balance = contract.functions.balanceOf(address)
            return balance / 10**6  # Convert from SUN to USDT
        except Exception as e:
            print(f"Error fetching USDT balance: {e}")
            return 0

    @staticmethod
    def transfer_trx(sender_private_key, recipient_address, amount_in_trx):
        """
        Transfers TRX from one wallet to another.
        """
        try:
            sender_private_key = PrivateKey(bytes.fromhex(sender_private_key))
            sender_address = sender_private_key.public_key.to_base58check_address()

            # Convert TRX to Sun (1 TRX = 1,000,000 Sun)
            amount_in_sun = int(amount_in_trx * 1_000_000)

            txn = (
                TronWallet.client.trx.transfer(sender_address, recipient_address, amount_in_sun)
                .build()
                .sign(sender_private_key)
            )

            return txn.broadcast()
        except Exception as e:
            print(f"Error sending TRX: {e}")
            return None

    @staticmethod
    def transfer_usdt(sender_private_key, recipient_address, amount_in_usdt):
        """
        Transfers USDT from one wallet to another.
        """
        try:
            sender_private_key = PrivateKey(bytes.fromhex(sender_private_key))
            sender_address = sender_private_key.public_key.to_base58check_address()

            contract = TronWallet.client.get_contract(TronWallet.USDT_CONTRACT).with_abi([
                {
                    "constant": False,
                    "inputs": [
                        {"name": "_to", "type": "address"},
                        {"name": "_value", "type": "uint256"}
                    ],
                    "name": "transfer",
                    "outputs": [{"name": "success", "type": "bool"}],
                    "payable": False,
                    "stateMutability": "Nonpayable",
                    "type": "Function",
                }
            ])

            amount_in_sun = int(amount_in_usdt * 1_000_000)  # Convert to 6 decimal places

            txn = (
                contract.functions.transfer(recipient_address, amount_in_sun)
                .with_owner(sender_address)
                .fee_limit(10_000_000)
                .build()
                .sign(sender_private_key)
            )

            return txn.broadcast()
        except Exception as e:
            print(f"Error sending USDT: {e}")
            return None


    def create_usdt_wallet(wallet_name):
        """
        Creates a new USDT wallet and returns its details.
        """
        private_key = PrivateKey.random()
        address = private_key.public_key.to_base58check_address()
        
        try :
            balance = TronWallet.get_usdt_balance(address)
        except Exception as e:
            print(f"Error creating wallet: {e}")
            balance = 0
            
        return {
            "private_key": private_key.hex(),  # Keep this secret!
            "public_key": address,
            "name": wallet_name,
            "balance": balance,
        }
        
        