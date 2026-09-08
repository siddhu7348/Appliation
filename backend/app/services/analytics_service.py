"""Store x category coverage analytics."""

from __future__ import annotations

import numpy as np

from app.core.cache import cache_get, cache_set
from app.ml.artifacts import get_store
from app.schemas.analytics import AnalyticsGrid, CategoryScore, HeatmapCell, StoreHealthRow

ANALYTICS_CACHE_KEY = "forecastiq:analytics:v1"


def build_analytics() -> AnalyticsGrid:
    artifacts = get_store()
    frame = artifacts.forecasts.copy()
    frame["relative_width"] = ((frame["p90"] - frame["p10"]) / frame["p50"].clip(lower=1e-6)).clip(
        0, 2
    )
    frame["coverage_probability"] = 1 - frame["relative_width"] / 2
    # Proxy MAPE: wider intervals and stronger anomalies mean less accurate points.
    frame["mape"] = (frame["relative_width"] * 12 + frame["anomaly_score"] * 8).round(2)

    grouped = (
        frame.groupby(["store_nbr", "family"])
        .agg(
            coverage_probability=("coverage_probability", "mean"),
            mape=("mape", "mean"),
            series_count=("p50", "size"),
        )
        .reset_index()
    )

    cells = [
        HeatmapCell(
            store_nbr=int(row.store_nbr),
            family=str(row.family),
            coverage_probability=round(float(row.coverage_probability), 4),
            mape=round(float(row.mape), 2),
            series_count=int(row.series_count),
        )
        for row in grouped.itertuples(index=False)
    ]

    by_family = (
        grouped.groupby("family")
        .agg(mape=("mape", "mean"), coverage_probability=("coverage_probability", "mean"))
        .reset_index()
        .sort_values("mape")
    )
    leaderboard = [
        CategoryScore(
            family=str(row.family),
            mape=round(float(row.mape), 2),
            coverage_probability=round(float(row.coverage_probability), 4),
            rank=index + 1,
        )
        for index, row in enumerate(by_family.itertuples(index=False))
    ]

    by_store = (
        grouped.groupby("store_nbr")
        .agg(mape=("mape", "mean"), coverage_probability=("coverage_probability", "mean"))
        .reset_index()
    )
    by_store["health_score"] = np.clip(
        by_store["coverage_probability"] * 100 - by_store["mape"] / 2, 0, 100
    )
    by_store = by_store.sort_values("health_score", ascending=False)
    ranking = [
        StoreHealthRow(
            store_nbr=int(row.store_nbr),
            health_score=round(float(row.health_score), 1),
            coverage_probability=round(float(row.coverage_probability), 4),
            mape=round(float(row.mape), 2),
            rank=index + 1,
        )
        for index, row in enumerate(by_store.itertuples(index=False))
    ]

    return AnalyticsGrid(
        stores=sorted(int(store) for store in grouped["store_nbr"].unique()),
        families=sorted(str(family) for family in grouped["family"].unique()),
        cells=cells,
        category_leaderboard=leaderboard,
        store_ranking=ranking,
        data_source="synthetic" if artifacts.is_synthetic else "artifacts",
    )


async def get_analytics() -> AnalyticsGrid:
    cached = await cache_get(ANALYTICS_CACHE_KEY)
    if cached:
        return AnalyticsGrid.model_validate(cached)
    grid = build_analytics()
    await cache_set(ANALYTICS_CACHE_KEY, grid.model_dump(mode="json"))
    return grid
