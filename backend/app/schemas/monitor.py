from datetime import date

from pydantic import BaseModel


class Scorecard(BaseModel):
    model_name: str
    current_mape: float
    previous_mape: float
    delta_pp: float
    trend: str
    status: str
    coverage_rate: float
    coverage_status: str


class ModelComparisonPoint(BaseModel):
    week_start: date
    values: dict[str, float]


class DriftStatus(BaseModel):
    triggered: bool
    mape_delta_pp: float
    consecutive_weeks: int
    message: str


class PerformanceMonitor(BaseModel):
    coverage_target: float
    scorecards: list[Scorecard]
    comparison: list[ModelComparisonPoint]
    models: list[str]
    drift: DriftStatus
    data_source: str
