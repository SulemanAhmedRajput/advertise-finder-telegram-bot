import beanie


class Token(Document):
    public_key: str
    private_key: str
    case_no: str
    user_id: str
