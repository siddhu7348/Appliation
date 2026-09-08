from datetime import date

from pydantic import BaseModel, Field


class SeriesRef(BaseModel):
    product_id: str
    store_nbr: int
    family: str


class ForecastPoint(BaseModel):
    forecast_date: date
    p10: float
    p50: float
    p90: float
    lgbm_point: float | None = None
    anomaly_score: float = Field(ge=0.0, le=1.0)
    is_holiday: bool = False
    oil_event: bool = False


class HistoryPoint(BaseModel):
    date: date
    actual: float
    predicted: float


class AttentionWeight(BaseModel):
    lag_days: int
    weight: float


class EventMarker(BaseModel):
    date: date
    type: str
    label: str


class ForecastDetail(BaseModel):
    series: SeriesRef
    horizon: list[ForecastPoint]
    history: list[HistoryPoint]
    attention: list[AttentionWeight]
    events: list[EventMarker]
    data_source: str


class CatalogResponse(BaseModel):
    stores: list[int]
    families: list[str]
    products: list[SeriesRef]
    series_count: int
    data_source: str
