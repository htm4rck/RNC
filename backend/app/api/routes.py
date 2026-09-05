from fastapi import APIRouter

from app.api.candidate_profiles import router as candidate_profiles_router
from app.models.health import HealthResponse

router = APIRouter()
router.include_router(candidate_profiles_router)


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="remote-career-navigator-api")
