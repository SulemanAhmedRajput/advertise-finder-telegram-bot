from typing import Optional
from beanie import Document, Indexed


class Wallet(Document):
    public_key: str
    private_key: str
    wallet_type: str
    name: str
    user_id: int
    deleted: bool = False

    class Settings:
        name = "wallets"
