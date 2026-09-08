"""Morning Brief aggregation, served from the Redis cache filled by the nightly job."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.ml.artifacts import get_store
from app.schemas.brief import (
    AccuracySummary,
    AnomalyFlag,
    MorningBrief,
    StockoutAlert,
    TopMover,
)

BRIEF_CACHE_PREFIX = "forecastiq:brief:v1"
UNIT_REVENUE = 4.75
SAFE_THRESHOLD_RATIO = 0.85


def cache_key(store_nbr: int | None) -> str:
    return f"{BRIEF_CACHE_PREFIX}:{store_nbr if store_nbr is not None else 'all'}"


def _scope(frame: pd.DataFrame, store_nbr: int | None) -> pd.DataFrame:
    if store_nbr is None:
        return frame
    return frame[frame["store_nbr"] == store_nbr]


def _health_score(frame: pd.DataFrame) -> float:
    """0-100 score from interval coverage probability and anomaly pressure."""
    if frame.empty:
        return 0.0
    relative_width = ((frame["p90"] - frame["p10"]) / frame["p50"].clip(lower=1e-6)).clip(0, 2)
    coverage_probability = float(np.mean(1 - relative_width / 2))
    anomaly_penalty = float(frame["anomaly_score"].mean()) * 25
    return round(max(0.0, min(100.0, coverage_probability * 100 - anomaly_penalty)), 1)


def _health_label(score: float) -> str:
    if score >= 75:
        return "healthy"
    if score >= 55:
        return "watch"
    return "at_risk"


def build_brief(store_nbr: int | None = None) -> MorningBrief:
    artifacts = get_store()
    frame = _scope(artifacts.forecasts, store_nbr)
    today = frame["forecast_date"].min() if not frame.empty else date.today()
    today = today if isinstance(today, date) else date.fromisoformat(str(today)[:10])

    today_rows = frame[frame["forecast_date"] == today]
    week_rows = frame[frame["forecast_date"] <= today + timedelta(days=6)]

    stockout = today_rows.copy()
    stockout["safe_threshold"] = stockout["p50"] * SAFE_THRESHOLD_RATIO
    stockout = stockout[stockout["p10"] < stockout["safe_threshold"]]
    stockout["revenue_impact"] = (stockout["safe_threshold"] - stockout["p10"]) * UNIT_REVENUE
    stockout = stockout.sort_values("revenue_impact", ascending=False).head(25)

    anomalies = week_rows[week_rows["anomaly_score"] > settings.anomaly_flag_threshold]
    anomalies = anomalies.sort_values("anomaly_score", ascending=False).head(25)

    movers = today_rows.sort_values("p50", ascending=False).head(10)

    metrics = artifacts.metrics
    latest_week = metrics["weekly"][-1]["models"].get(metrics.get("primary_model", "TFT"))

    return MorningBrief(
        store_health_score=_health_score(today_rows),
        health_label=_health_label(_health_score(today_rows)),
        generated_at=today,
        stockout_alerts=[
            StockoutAlert(
                product_id=str(row.product_id),
                store_nbr=int(row.store_nbr),
                family=str(row.family),
                p10=float(row.p10),
                p50=float(row.p50),
                safe_threshold=round(float(row.safe_threshold), 2),
                revenue_impact=round(float(row.revenue_impact), 2),
            )
            for row in stockout.itertuples(index=False)
        ],
        anomaly_flags=[
            AnomalyFlag(
                product_id=str(row.product_id),
                store_nbr=int(row.store_nbr),
                family=str(row.family),
                forecast_date=row.forecast_date,
                anomaly_score=float(row.anomaly_score),
                p50=float(row.p50),
            )
            for row in anomalies.itertuples(index=False)
        ],
        top_movers=[
            TopMover(
                product_id=str(row.product_id),
                store_nbr=int(row.store_nbr),
                family=str(row.family),
                p50=float(row.p50),
                p90=float(row.p90),
                anomaly_score=float(row.anomaly_score),
            )
            for row in movers.itertuples(index=False)
        ],
        yesterday_accuracy=AccuracySummary(
            mape=float(latest_week["mape"]),
            coverage_rate=float(latest_week["coverage_rate"]),
            coverage_target=settings.coverage_target,
            as_of=today - timedelta(days=1),
        ),
        data_source="synthetic" if artifacts.is_synthetic else "artifacts",
    )


async def get_brief(store_nbr: int | None = None) -> MorningBrief:
    key = cache_key(store_nbr)
    cached = await cache_get(key)
    if cached:
        brief = MorningBrief.model_validate(cached)
        brief.cached = True
        return brief

    brief = build_brief(store_nbr)
    await cache_set(key, brief.model_dump(mode="json"))
    return brief
