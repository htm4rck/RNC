from datetime import datetime

from pydantic import BaseModel, Field


class CandidateProfileCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    headline: str = Field(min_length=2, max_length=220)
    country: str = Field(min_length=2, max_length=80)
    years_experience: int = Field(ge=0, le=60)
    english_level: str = Field(min_length=2, max_length=40)


class CandidateProfileRead(CandidateProfileCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
