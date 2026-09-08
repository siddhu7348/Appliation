from fastapi import APIRouter

from app.api.routes import analytics, auth, brief, forecast, inventory, monitor

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(brief.router)
api_router.include_router(forecast.router)
api_router.include_router(inventory.router)
api_router.include_router(monitor.router)
api_router.include_router(analytics.router)
