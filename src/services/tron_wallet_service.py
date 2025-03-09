from tronpy import Tron
from tronpy.keys import PrivateKey

# Connect to the TRON mainnet or testnet
client = Tron(network='shasta')  # Use 'mainnet' for live transactions

# Function to create a new TRON wallet
def create_wallet():
    private_key = PrivateKey.random()
    address = private_key.public_key.to_base58check_address()
    return {
        "private_key": private_key.hex(),  # Keep this secret
        "address": address,
    }

# Function to check the balance of a TRON wallet
def get_trx_balance(address):
    return client.get_account_balance(address)  # Balance is in TRX

# Function to transfer TRX from one wallet to another
def transfer_trx(sender_private_key, recipient_address, amount_in_trx):
    sender_private_key = PrivateKey(bytes.fromhex(sender_private_key))
    sender_address = sender_private_key.public_key.to_base58check_address()

    # Convert TRX to Sun (1 TRX = 1,000,000 Sun)
    amount_in_sun = int(amount_in_trx * 1_000_000)

    txn = (
        client.trx.transfer(sender_address, recipient_address, amount_in_sun)
        .build()
        .sign(sender_private_key)
    )

    # Broadcast the transaction
    return txn.broadcast()

# Function to check the USDT balance of a wallet
def get_usdt_balance(address):
    usdt_contract = client.get_contract("TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj")  # TRC20 USDT contract
    return usdt_contract.functions.balanceOf(address) / 1_000_000  # Convert from 6 decimal places

# Function to transfer USDT
def transfer_usdt(sender_private_key, recipient_address, amount_in_usdt):
    sender_private_key = PrivateKey(bytes.fromhex(sender_private_key))
    sender_address = sender_private_key.public_key.to_base58check_address()

    usdt_contract = client.get_contract("TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj")  # TRC20 USDT contract
    amount_in_sun = int(amount_in_usdt * 1_000_000)  # Convert to 6 decimal places

    txn = (
        usdt_contract.functions.transfer(recipient_address, amount_in_sun)
        .with_owner(sender_address)
        .fee_limit(10_000_000)
        .build()
        .sign(sender_private_key)
    )

    return txn.broadcast()

def fund_wallet(sender_private_key, recipient_address, amount_in_trx):
    sender_private_key = PrivateKey(bytes.fromhex(sender_private_key))
    sender_address = sender_private_key.public_key.to_base58check_address()

    # Convert TRX to Sun (1 TRX = 1,000,000 Sun)
    amount_in_sun = int(amount_in_trx * 1_000_000)

    txn = (
        client.trx.transfer(sender_address, recipient_address, amount_in_sun)
        .build()
        .sign(sender_private_key)
    )

    return txn.broadcast()



if __name__ == "__main__":
    # Create a new wallet
    new_wallet = create_wallet()
    print("New Wallet:", new_wallet)

    # Fund the new wallet with 10 TRX
    sender_private_key = "2f60abed403a9a68426fe106774dd8f19f91ed1e1b8534d12a970c0911ffdeb3"
    recipient_address = new_wallet["address"]
    
    print("Funding new wallet with 10 TRX...")
    tx_result = fund_wallet(sender_private_key, recipient_address, 10)
    print("Funding transaction:", tx_result)

    # Now, check TRX balance
    balance = get_trx_balance(new_wallet["address"])
    print("TRX Balance:", balance, "TRX")
