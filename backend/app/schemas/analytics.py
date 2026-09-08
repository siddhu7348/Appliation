from pydantic import BaseModel


class HeatmapCell(BaseModel):
    store_nbr: int
    family: str
    coverage_probability: float
    mape: float
    series_count: int


class CategoryScore(BaseModel):
    family: str
    mape: float
    coverage_probability: float
    rank: int


class StoreHealthRow(BaseModel):
    store_nbr: int
    health_score: float
    coverage_probability: float
    mape: float
    rank: int


class AnalyticsGrid(BaseModel):
    stores: list[int]
    families: list[str]
    cells: list[HeatmapCell]
    category_leaderboard: list[CategoryScore]
    store_ranking: list[StoreHealthRow]
    data_source: str
