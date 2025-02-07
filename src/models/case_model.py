from beanie import Document
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class Case(Document):
    title: str
    description: Optional[str] = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()

    class Settings:
        collection = "cases"

    def __repr__(self):
        return f"<Case(id={self.id}, title={self.title}, created_at={self.created_at})>"
