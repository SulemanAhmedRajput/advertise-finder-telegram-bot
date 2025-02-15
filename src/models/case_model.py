from beanie import Document, Indexed
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime


class Case(Document):
    user_id: int
    case_no: str
    name: str
    mobile: str
    person_name: str
    relationship: str
    photo_path: Optional[str] = None
    last_seen_location: str
    sex: str
    age: int
    hair_color: str
    eye_color: str
    height: float
    weight: float
    distinctive_features: Optional[str] = None
    reward: Optional[float] = None
    reward_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    finder: Optional[str] = None

    class Settings:
        name = "cases"  # The name of the collection in MongoDB

    @validator("sex")
    def validate_sex(cls, v):
        if v not in ["male", "female", "other"]:
            raise ValueError("Invalid sex")
        return v

    @validator("age")
    def validate_age(cls, v):
        if v < 0:
            raise ValueError("Age must be a positive integer")
        return v

    @validator("height", "weight")
    def validate_positive(cls, v):
        if v <= 0:
            raise ValueError("Height and weight must be positive values")
        return v
