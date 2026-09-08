"""Nightly forecasting batch and drift monitoring.

Timeline (UTC): 23:00 ingest -> feature engineering (11 features, IsolationForest
anomaly scores with CV-based dynamic contamination) -> TFT + LightGBM inference over
all series -> PostgreSQL write -> Redis refresh -> anomaly alert emails. Sized to
finish well before the 08:00 store open.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from datetime import date

import pandas as pd
from sqlalchemy import delete, select

from app.core.cache import cache_delete_prefix, cache_set, close_cache
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.ml import features as feature_engineering
from app.ml.artifacts import load_store
from app.models.forecast import ForecastRecord
from app.models.metrics import DriftEvent, ModelMetric
from app.models.user import User, UserRole
from app.services import analytics_service, brief_service, forecast_service, monitor_service
from app.services.email_service import anomaly_alert_body, drift_alert_body, send_email
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def _recompute_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Rebuild the 11 engineered features per series and rescore anomalies.

    Features are computed per product-store series, then pooled into a single
    IsolationForest fit whose contamination is derived from the observed CV.
    """
    frame = frame.sort_values(["product_id", "store_nbr", "forecast_date"]).reset_index(drop=True)
    blocks = []
    for _, series in frame.groupby(["product_id", "store_nbr"], sort=False):
        blocks.append(
            feature_engineering.build_features(
                pd.DataFrame(
                    {
                        "date": pd.to_datetime(series["forecast_date"]),
                        "sales": series["p50"].to_numpy(),
                        "is_holiday": series["is_holiday"].astype(int).to_numpy(),
                    }
                )
            )
        )
    engineered = pd.concat(blocks, ignore_index=True)
    scores = feature_engineering.anomaly_scores(engineered)
    if len(scores) == len(frame):
        frame["anomaly_score"] = scores.round(4)
    return frame


async def _persist_forecasts(frame: pd.DataFrame) -> int:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ForecastRecord))
        records = [
            ForecastRecord(
                product_id=str(row.product_id),
                store_nbr=int(row.store_nbr),
                family=str(row.family),
                forecast_date=row.forecast_date,
                p10=float(row.p10),
                p50=float(row.p50),
                p90=float(row.p90),
                lgbm_point=float(row.lgbm_point),
                anomaly_score=float(row.anomaly_score),
                is_holiday=bool(row.is_holiday),
                oil_event=bool(row.oil_event),
            )
            for row in frame.itertuples(index=False)
        ]
        session.add_all(records)
        await session.commit()
        return len(records)


async def _refresh_cache() -> None:
    for prefix in ("forecastiq:brief", "forecastiq:series", "forecastiq:catalog"):
        await cache_delete_prefix(prefix)
    await cache_set(
        forecast_service.CATALOG_CACHE_KEY,
        (await forecast_service.get_catalog()).model_dump(mode="json"),
    )
    await cache_set(
        brief_service.cache_key(None), brief_service.build_brief().model_dump(mode="json")
    )
    await cache_set(
        monitor_service.MONITOR_CACHE_KEY, monitor_service.build_monitor().model_dump(mode="json")
    )
    await cache_set(
        analytics_service.ANALYTICS_CACHE_KEY,
        analytics_service.build_analytics().model_dump(mode="json"),
    )


async def _alert_high_anomalies(frame: pd.DataFrame) -> int:
    flagged = frame[frame["anomaly_score"] > settings.anomaly_alert_threshold]
    if flagged.empty:
        return 0

    by_store: dict[int, list[dict]] = defaultdict(list)
    for row in flagged.itertuples(index=False):
        by_store[int(row.store_nbr)].append(
            {
                "product_id": str(row.product_id),
                "forecast_date": str(row.forecast_date),
                "anomaly_score": float(row.anomaly_score),
                "p50": float(row.p50),
            }
        )

    sent = 0
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                User.role == UserRole.STORE_MANAGER.value, User.is_active.is_(True)
            )
        )
        managers = list(result.scalars().all())

    for store_nbr, products in by_store.items():
        recipients = [
            manager.email for manager in managers if manager.store_nbr in (store_nbr, None)
        ]
        if send_email(
            recipients,
            f"[ForecastIQ] {len(products)} high-anomaly products - store {store_nbr}",
            anomaly_alert_body(store_nbr, products[:25]),
        ):
            sent += 1
    return sent


async def _run_batch() -> dict:
    started = time.perf_counter()
    store = load_store(force_reload=True)
    frame = _recompute_features(store.forecasts)
    store.forecasts = frame

    written = await _persist_forecasts(frame)
    await _refresh_cache()
    alerts = await _alert_high_anomalies(frame)
    await close_cache()

    duration = round(time.perf_counter() - started, 2)
    logger.info("nightly batch finished in %ss: %s rows, %s alerts", duration, written, alerts)
    return {
        "rows_written": written,
        "series": int(frame[["product_id", "store_nbr"]].drop_duplicates().shape[0]),
        "alerts_sent": alerts,
        "duration_seconds": duration,
        "data_source": "synthetic" if store.is_synthetic else "artifacts",
    }


@celery_app.task(name="app.tasks.nightly.run_nightly_batch")
def run_nightly_batch() -> dict:
    return asyncio.run(_run_batch())


async def _persist_metrics() -> None:
    weekly = load_store().metrics["weekly"]
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ModelMetric))
        for week in weekly:
            for model_name, values in week["models"].items():
                session.add(
                    ModelMetric(
                        week_start=date.fromisoformat(week["week_start"]),
                        model_name=model_name,
                        mape=float(values["mape"]),
                        coverage_rate=float(values["coverage_rate"]),
                    )
                )
        await session.commit()


async def _check_drift() -> dict:
    await _persist_metrics()
    status = monitor_service.detect_drift()
    if status.triggered:
        async with AsyncSessionLocal() as session:
            session.add(
                DriftEvent(
                    mape_delta_pp=status.mape_delta_pp,
                    consecutive_weeks=status.consecutive_weeks,
                    message=status.message,
                )
            )
            await session.commit()
            result = await session.execute(
                select(User).where(
                    User.role.in_([UserRole.HQ.value, UserRole.ADMIN.value]),
                    User.is_active.is_(True),
                )
            )
            recipients = [user.email for user in result.scalars().all()]
        send_email(
            recipients,
            "[ForecastIQ] Model drift detected - retraining recommended",
            drift_alert_body(status.message, status.mape_delta_pp, status.consecutive_weeks),
        )
    await cache_set(
        monitor_service.DRIFT_CACHE_KEY, status.model_dump(mode="json"), ttl=60 * 60 * 24
    )
    await close_cache()
    return status.model_dump(mode="json")


@celery_app.task(name="app.tasks.nightly.check_model_drift")
def check_model_drift() -> dict:
    return asyncio.run(_check_drift())
