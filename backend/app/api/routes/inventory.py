from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user, require_roles
from app.models.user import User, UserRole
from app.schemas.inventory import (
    ConfidenceMode,
    ExportRequest,
    InventoryResponse,
    OverrideCreate,
    OverrideOut,
)
from app.services import export_service, inventory_service

router = APIRouter(prefix="/inventory", tags=["inventory"])

MANAGER_ROLES = (
    UserRole.STORE_MANAGER,
    UserRole.REGIONAL_DIRECTOR,
    UserRole.HQ,
    UserRole.ADMIN,
)


@router.get("/recommendations", response_model=InventoryResponse)
async def recommendations(
    confidence_mode: ConfidenceMode = Query(default=ConfidenceMode.BALANCED),
    store_nbr: int | None = Query(default=None, ge=1, le=54),
    family: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=200, ge=1, le=1000),
    user: User = Depends(get_current_user),
) -> InventoryResponse:
    scope = user.store_nbr if user.role == UserRole.STORE_MANAGER.value else store_nbr
    return inventory_service.build_recommendations(confidence_mode, scope, family, limit)


@router.post("/overrides", response_model=OverrideOut, status_code=status.HTTP_201_CREATED)
async def create_override(
    payload: OverrideCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(require_roles(*MANAGER_ROLES)),
) -> OverrideOut:
    override = await inventory_service.log_override(session, user.id, payload)
    return OverrideOut.model_validate(override)


@router.get("/overrides", response_model=list[OverrideOut])
async def list_overrides(
    store_nbr: int | None = Query(default=None, ge=1, le=54),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
    _: User = Depends(get_current_user),
) -> list[OverrideOut]:
    rows = await inventory_service.list_overrides(session, store_nbr, limit)
    return [OverrideOut.model_validate(row) for row in rows]


@router.post("/export/{export_format}")
async def export_purchase_order(
    export_format: str,
    payload: ExportRequest,
    _: User = Depends(require_roles(*MANAGER_ROLES)),
) -> Response:
    if export_format == "xlsx":
        content = export_service.build_excel(payload)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif export_format == "pdf":
        content = export_service.build_pdf(payload)
        media_type = "application/pdf"
    else:
        return Response(
            content='{"detail":"Unsupported export format. Use xlsx or pdf."}',
            media_type="application/json",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    filename = f"forecastiq-purchase-order.{export_format}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
