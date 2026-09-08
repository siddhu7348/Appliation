"""Forecast read model. Redis-cached, artifact/synthetic backed."""

from __future__ import annotations

from datetime import date

from app.core.cache import cache_get, cache_set
from app.ml.artifacts import get_store
from app.schemas.forecast import (
    AttentionWeight,
    CatalogResponse,
    EventMarker,
    ForecastDetail,
    ForecastPoint,
    HistoryPoint,
    SeriesRef,
)

CATALOG_CACHE_KEY = "forecastiq:catalog:v1"
SERIES_CACHE_PREFIX = "forecastiq:series:v1:"


def _data_source() -> str:
    return "synthetic" if get_store().is_synthetic else "artifacts"


async def get_catalog() -> CatalogResponse:
    cached = await cache_get(CATALOG_CACHE_KEY)
    if cached:
        return CatalogResponse.model_validate(cached)

    catalog = get_store().catalog()
    payload = CatalogResponse(
        stores=sorted(int(store) for store in catalog["store_nbr"].unique()),
        families=sorted(str(family) for family in catalog["family"].unique()),
        products=[
            SeriesRef(
                product_id=str(row.product_id),
                store_nbr=int(row.store_nbr),
                family=str(row.family),
            )
            for row in catalog.itertuples(index=False)
        ],
        series_count=int(len(catalog)),
        data_source=_data_source(),
    )
    await cache_set(CATALOG_CACHE_KEY, payload.model_dump(mode="json"))
    return payload


def series_cache_key(product_id: str, store_nbr: int) -> str:
    return f"{SERIES_CACHE_PREFIX}{product_id}:{store_nbr}"


def build_series_detail(product_id: str, store_nbr: int) -> ForecastDetail | None:
    store = get_store()
    frame = store.series_forecast(product_id, store_nbr)
    if frame.empty:
        return None

    horizon = [
        ForecastPoint(
            forecast_date=_as_date(row.forecast_date),
            p10=float(row.p10),
            p50=float(row.p50),
            p90=float(row.p90),
            lgbm_point=None if row.lgbm_point is None else float(row.lgbm_point),
            anomaly_score=float(row.anomaly_score),
            is_holiday=bool(row.is_holiday),
            oil_event=bool(row.oil_event),
        )
        for row in frame.itertuples(index=False)
    ]
    events = [
        EventMarker(date=point.forecast_date, type="holiday", label="National holiday")
        for point in horizon
        if point.is_holiday
    ] + [
        EventMarker(date=point.forecast_date, type="oil_price", label="Oil price shock")
        for point in horizon
        if point.oil_event
    ]

    return ForecastDetail(
        series=SeriesRef(
            product_id=product_id,
            store_nbr=store_nbr,
            family=str(frame.iloc[0]["family"]),
        ),
        horizon=horizon,
        history=[HistoryPoint(**point) for point in store.history(product_id, store_nbr)],
        attention=[AttentionWeight(**point) for point in store.attention(product_id, store_nbr)],
        events=sorted(events, key=lambda event: event.date),
        data_source=_data_source(),
    )


async def get_series_detail(product_id: str, store_nbr: int) -> ForecastDetail | None:
    key = series_cache_key(product_id, store_nbr)
    cached = await cache_get(key)
    if cached:
        return ForecastDetail.model_validate(cached)

    detail = build_series_detail(product_id, store_nbr)
    if detail is None:
        return None
    await cache_set(key, detail.model_dump(mode="json"))
    return detail


def _as_date(value) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])
