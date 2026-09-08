"""Model performance scorecards and rolling-MAPE drift detection."""

from __future__ import annotations

from datetime import date

from app.core.cache import cache_get, cache_set
from app.core.config import settings
from app.ml.artifacts import get_store
from app.schemas.monitor import (
    DriftStatus,
    ModelComparisonPoint,
    PerformanceMonitor,
    Scorecard,
)

MONITOR_CACHE_KEY = "forecastiq:monitor:v1"
DRIFT_CACHE_KEY = "forecastiq:drift:v1"


def _status_for_mape(delta_pp: float) -> str:
    if delta_pp <= 0:
        return "green"
    if delta_pp <= 2:
        return "amber"
    return "red"


def _coverage_status(coverage: float) -> str:
    target = settings.coverage_target
    if coverage >= target:
        return "green"
    if coverage >= target - 0.05:
        return "amber"
    return "red"


def detect_drift() -> DriftStatus:
    """Warn when rolling MAPE degrades >5pp across N consecutive weeks."""
    weekly = get_store().metrics["weekly"]
    primary = get_store().metrics.get("primary_model", "TFT")
    window = settings.drift_consecutive_weeks
    if len(weekly) < window + 1:
        return DriftStatus(
            triggered=False, mape_delta_pp=0.0, consecutive_weeks=0, message="Insufficient history"
        )

    series = [week["models"][primary]["mape"] for week in weekly]
    consecutive = 0
    for index in range(len(series) - window, len(series)):
        if series[index] > series[index - 1]:
            consecutive += 1
        else:
            consecutive = 0
    delta = round(series[-1] - series[-1 - window], 2)
    triggered = consecutive >= window and delta > settings.drift_mape_threshold_pp
    message = (
        f"{primary} MAPE rose {delta:.2f}pp over {window} consecutive weeks - "
        "retraining recommended."
        if triggered
        else f"{primary} MAPE change over {window} weeks: {delta:+.2f}pp (within tolerance)."
    )
    return DriftStatus(
        triggered=triggered,
        mape_delta_pp=delta,
        consecutive_weeks=consecutive,
        message=message,
    )


def build_monitor() -> PerformanceMonitor:
    artifacts = get_store()
    weekly = artifacts.metrics["weekly"]
    models = list(weekly[-1]["models"].keys())
    current, previous = weekly[-1], weekly[-2] if len(weekly) > 1 else weekly[-1]

    scorecards = []
    for model in models:
        current_mape = float(current["models"][model]["mape"])
        previous_mape = float(previous["models"][model]["mape"])
        delta = round(current_mape - previous_mape, 2)
        coverage = float(current["models"][model]["coverage_rate"])
        scorecards.append(
            Scorecard(
                model_name=model,
                current_mape=current_mape,
                previous_mape=previous_mape,
                delta_pp=delta,
                trend="up" if delta > 0 else "down" if delta < 0 else "flat",
                status=_status_for_mape(delta),
                coverage_rate=coverage,
                coverage_status=_coverage_status(coverage),
            )
        )

    comparison = [
        ModelComparisonPoint(
            week_start=date.fromisoformat(week["week_start"]),
            values={model: float(week["models"][model]["mape"]) for model in models},
        )
        for week in weekly
    ]

    return PerformanceMonitor(
        coverage_target=settings.coverage_target,
        scorecards=scorecards,
        comparison=comparison,
        models=models,
        drift=detect_drift(),
        data_source="synthetic" if artifacts.is_synthetic else "artifacts",
    )


async def get_monitor() -> PerformanceMonitor:
    cached = await cache_get(MONITOR_CACHE_KEY)
    if cached:
        return PerformanceMonitor.model_validate(cached)
    monitor = build_monitor()
    await cache_set(MONITOR_CACHE_KEY, monitor.model_dump(mode="json"))
    return monitor


async def get_drift_status() -> DriftStatus:
    cached = await cache_get(DRIFT_CACHE_KEY)
    if cached:
        return DriftStatus.model_validate(cached)
    status = detect_drift()
    await cache_set(DRIFT_CACHE_KEY, status.model_dump(mode="json"), ttl=3600)
    return status
