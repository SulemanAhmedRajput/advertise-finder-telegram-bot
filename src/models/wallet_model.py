from beanie import Document, Indexed


class Wallet(Document):
    public_key: str
    private_key: str
    case_no: str
    user_id: str
