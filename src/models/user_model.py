from beanie import Document
from pydantic import Field


class User(Document):
    tl_id: int = Field(...)
    lang: str = Field(...)