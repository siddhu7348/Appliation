from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.analytics import AnalyticsGrid
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsGrid)
async def analytics(_: User = Depends(get_current_user)) -> AnalyticsGrid:
    return await analytics_service.get_analytics()
