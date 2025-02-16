from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from beanie import Document
from enum import Enum

class CaseStatus(Enum):
    DRAFT = "draft"
    ADVERTISE = "advertise"

class Case(Document):
    user_id: int
    country: Optional[str] = None
    city: Optional[str] = None
    status: CaseStatus = Field(default=CaseStatus.DRAFT)
    case_no: Optional[str] = None
    name: Optional[str] = None
    mobile: Optional[str] = None
    person_name: Optional[str] = None
    relationship: Optional[str] = None
    photo_path: Optional[str] = None
    last_seen_location: Optional[str] = None
    sex: Optional[str] = None
    age: Optional[int] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    distinctive_features: Optional[str] = None
    reward: Optional[float] = None
    reward_type: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "cases"  # The name of the collection in MongoDB

    @validator("sex")
    def validate_sex(cls, v):
        if v and v not in ["male", "female", "other"]:
            raise ValueError("Invalid sex")
        return v

    @validator("age")
    def validate_age(cls, v):
        if v and v < 0:
            raise ValueError("Age must be a positive integer")
        return v

    @validator("height", "weight")
    def validate_positive(cls, v):
        if v and v <= 0:
            raise ValueError("Height and weight must be positive values")
        return v
