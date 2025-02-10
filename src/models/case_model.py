from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Case(Document):
    user_id: int
    case_no: str
    name: str
    mobile: str
    person_name: str
    relationship: str
    photo_path: Optional[str]
    last_seen_location: str
    sex: str
    age: str
    hair_color: str
    eye_color: str
    height: str
    weight: str
    distinctive_features: str
    reward: float
    reward_type: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    finder: str = None

    class Settings:
        name = "cases"  # The name of the collection in MongoDB
