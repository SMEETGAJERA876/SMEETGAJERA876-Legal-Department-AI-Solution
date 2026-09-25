from fastapi import APIRouter

from app.core.config import get_settings
from app.db.session import check_database_connection
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Report API liveness and whether the database is reachable."""
    database_ok = check_database_connection()
    return HealthResponse(
        status="ok" if database_ok else "degraded",
        app=get_settings().app_name,
        database="connected" if database_ok else "unavailable",
    )
