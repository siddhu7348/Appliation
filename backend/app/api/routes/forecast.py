from fastapi import APIRouter, Depends, HTTPException, Path, status

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.forecast import CatalogResponse, ForecastDetail
from app.services import forecast_service

router = APIRouter(prefix="/forecast", tags=["forecast"])


@router.get("/catalog", response_model=CatalogResponse)
async def catalog(_: User = Depends(get_current_user)) -> CatalogResponse:
    return await forecast_service.get_catalog()


@router.get("/{product_id}/{store_nbr}", response_model=ForecastDetail)
async def series_detail(
    product_id: str = Path(min_length=1, max_length=64),
    store_nbr: int = Path(ge=1, le=54),
    _: User = Depends(get_current_user),
) -> ForecastDetail:
    detail = await forecast_service.get_series_detail(product_id, store_nbr)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No forecast for product '{product_id}' at store {store_nbr}",
        )
    return detail
