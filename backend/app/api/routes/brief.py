from fastapi import APIRouter, Depends, Query

from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.schemas.brief import MorningBrief
from app.services import brief_service

router = APIRouter(prefix="/brief", tags=["morning-brief"])


@router.get("", response_model=MorningBrief)
async def morning_brief(
    store_nbr: int | None = Query(default=None, ge=1, le=54),
    user: User = Depends(get_current_user),
) -> MorningBrief:
    """Store managers are always scoped to their own store."""
    scope = store_nbr
    if user.role == UserRole.STORE_MANAGER.value:
        scope = user.store_nbr
    return await brief_service.get_brief(scope)
