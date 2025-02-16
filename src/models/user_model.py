from typing import List
from beanie import Document
from pydantic import Field


class User(Document):
    tl_id: int = Field(...)
    lang: str = Field(...)
    mobile_numbers: List[str] = Field(default_factory=list)  # Adding mobile_numbers field
