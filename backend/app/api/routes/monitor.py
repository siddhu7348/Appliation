from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.monitor import DriftStatus, PerformanceMonitor
from app.services import monitor_service

router = APIRouter(prefix="/monitor", tags=["model-monitor"])


@router.get("", response_model=PerformanceMonitor)
async def performance(_: User = Depends(get_current_user)) -> PerformanceMonitor:
    return await monitor_service.get_monitor()


@router.get("/drift", response_model=DriftStatus)
async def drift(_: User = Depends(get_current_user)) -> DriftStatus:
    return await monitor_service.get_drift_status()
