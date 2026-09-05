from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.candidate_profile import CandidateProfile
from app.schemas.candidate_profile import CandidateProfileCreate, CandidateProfileRead

router = APIRouter(prefix="/candidate-profiles", tags=["candidate profiles"])
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=CandidateProfileRead, status_code=201)
def create_candidate_profile(
    payload: CandidateProfileCreate,
    db: DatabaseSession,
) -> CandidateProfile:
    candidate_profile = CandidateProfile(**payload.model_dump())
    db.add(candidate_profile)
    db.commit()
    db.refresh(candidate_profile)
    return candidate_profile


@router.get("", response_model=list[CandidateProfileRead])
def list_candidate_profiles(db: DatabaseSession) -> list[CandidateProfile]:
    return list(db.scalars(select(CandidateProfile).order_by(CandidateProfile.created_at.desc())))
