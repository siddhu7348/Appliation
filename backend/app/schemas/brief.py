from datetime import date

from pydantic import BaseModel


class StockoutAlert(BaseModel):
    product_id: str
    store_nbr: int
    family: str
    p10: float
    p50: float
    safe_threshold: float
    revenue_impact: float


class AnomalyFlag(BaseModel):
    product_id: str
    store_nbr: int
    family: str
    forecast_date: date
    anomaly_score: float
    p50: float


class TopMover(BaseModel):
    product_id: str
    store_nbr: int
    family: str
    p50: float
    p90: float
    anomaly_score: float


class AccuracySummary(BaseModel):
    mape: float
    coverage_rate: float
    coverage_target: float
    as_of: date


class MorningBrief(BaseModel):
    store_health_score: float
    health_label: str
    generated_at: date
    stockout_alerts: list[StockoutAlert]
    anomaly_flags: list[AnomalyFlag]
    top_movers: list[TopMover]
    yesterday_accuracy: AccuracySummary
    data_source: str
    cached: bool = False
