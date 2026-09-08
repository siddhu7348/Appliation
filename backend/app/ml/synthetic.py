"""Synthetic demo data generator.

Used whenever the pre-generated ML artifacts are absent from ``/artifacts`` so the
application always boots with a realistic Corporacion Favorita shaped dataset:
54 stores x 33 categories (1612 product-store series), 16-day P10/P50/P90 paths,
90-day attention weights and IsolationForest style anomaly scores.
"""

from __future__ import annotations

import zlib
from datetime import date, timedelta

import numpy as np
import pandas as pd

N_STORES = 54
N_SERIES = 1612
HORIZON_DAYS = 16
LOOKBACK_DAYS = 90
ATTENTION_PEAKS = (7, 14, 21, 28)

FAMILIES: list[str] = [
    "AUTOMOTIVE",
    "BABY CARE",
    "BEAUTY",
    "BEVERAGES",
    "BOOKS",
    "BREAD/BAKERY",
    "CELEBRATION",
    "CLEANING",
    "DAIRY",
    "DELI",
    "EGGS",
    "FROZEN FOODS",
    "GROCERY I",
    "GROCERY II",
    "HARDWARE",
    "HOME AND KITCHEN I",
    "HOME AND KITCHEN II",
    "HOME APPLIANCES",
    "HOME CARE",
    "LADIESWEAR",
    "LAWN AND GARDEN",
    "LINGERIE",
    "LIQUOR,WINE,BEER",
    "MAGAZINES",
    "MEATS",
    "PERSONAL CARE",
    "PET SUPPLIES",
    "PLAYERS AND ELECTRONICS",
    "POULTRY",
    "PREPARED FOODS",
    "PRODUCE",
    "SCHOOL AND OFFICE SUPPLIES",
    "SEAFOOD",
]

REASON_CODES = [
    "promotion_planned",
    "supplier_constraint",
    "local_event",
    "storage_limit",
    "model_underestimates",
    "model_overestimates",
]

MODEL_NAMES = ["TFT", "LightGBM", "ARIMA", "Chronos-Bolt-Base 2024"]


def _series_seed(product_id: str, store_nbr: int) -> int:
    """Process-stable seed so every worker generates the same demo dataset."""
    return zlib.crc32(f"{product_id}|{store_nbr}".encode())


def build_series_catalog() -> pd.DataFrame:
    """Deterministic 1612-row catalog of product-store series.

    Not every store carries every category, so the 54 x 33 grid is thinned evenly
    down to the 1612 active series while keeping all stores and families present.
    """
    grid = [
        {
            "product_id": f"SKU-{family_idx:02d}",
            "store_nbr": store_nbr,
            "family": family,
        }
        for store_nbr in range(1, N_STORES + 1)
        for family_idx, family in enumerate(FAMILIES)
    ]
    drop_count = len(grid) - N_SERIES
    dropped = {round(index * len(grid) / drop_count) for index in range(drop_count)}
    return pd.DataFrame([row for index, row in enumerate(grid) if index not in dropped])


def _holiday_dates(start: date, days: int) -> set[date]:
    return {start + timedelta(days=offset) for offset in (2, 9, 13) if offset < days}


def _oil_event_dates(start: date, days: int) -> set[date]:
    return {start + timedelta(days=offset) for offset in (4, 11) if offset < days}


def build_forecast_frame(start_date: date | None = None) -> pd.DataFrame:
    """16-day probabilistic forecast for every series."""
    start = start_date or date.today()
    catalog = build_series_catalog()
    holidays = _holiday_dates(start, HORIZON_DAYS)
    oil_events = _oil_event_dates(start, HORIZON_DAYS)

    columns: dict[str, list] = {
        key: []
        for key in (
            "product_id",
            "store_nbr",
            "family",
            "forecast_date",
            "p10",
            "p50",
            "p90",
            "lgbm_point",
            "anomaly_score",
            "is_holiday",
            "oil_event",
        )
    }
    for row in catalog.itertuples(index=False):
        rng = np.random.default_rng(_series_seed(row.product_id, row.store_nbr))
        base = float(rng.uniform(12, 480))
        trend = float(rng.uniform(-0.004, 0.008))
        weekly_amp = float(rng.uniform(0.08, 0.32))
        noise_scale = float(rng.uniform(0.05, 0.18))

        dates = [start + timedelta(days=day) for day in range(HORIZON_DAYS)]
        day_index = np.arange(HORIZON_DAYS)
        weekday = np.array([d.weekday() for d in dates])
        seasonal = 1 + weekly_amp * np.sin(2 * np.pi * (weekday + 1) / 7)
        holiday_mask = np.array([d in holidays for d in dates])
        oil_mask = np.array([d in oil_events for d in dates])

        p50 = base * (1 + trend * day_index) * seasonal
        p50 = p50 * np.where(holiday_mask, 1.35, 1.0)
        p50 = p50 * np.where(oil_mask, 0.93, 1.0)
        p50 = p50 * (1 + rng.normal(0, noise_scale / 3, HORIZON_DAYS))
        p50 = np.clip(p50, 1.0, None)

        # Uncertainty widens with the forecast horizon.
        spread = noise_scale * (1 + day_index / HORIZON_DAYS)
        p10 = np.clip(p50 * (1 - 1.28 * spread), 0.0, None)
        p90 = p50 * (1 + 1.28 * spread)
        lgbm = np.clip(p50 * (1 + rng.normal(0, 0.05, HORIZON_DAYS)), 0.0, None)

        anomaly = np.clip(
            rng.beta(2.0, 6.0, HORIZON_DAYS) + 0.25 * holiday_mask + 0.12 * oil_mask, 0.0, 1.0
        )

        columns["product_id"].extend([row.product_id] * HORIZON_DAYS)
        columns["store_nbr"].extend([row.store_nbr] * HORIZON_DAYS)
        columns["family"].extend([row.family] * HORIZON_DAYS)
        columns["forecast_date"].extend(dates)
        columns["p10"].extend(np.round(p10, 2).tolist())
        columns["p50"].extend(np.round(p50, 2).tolist())
        columns["p90"].extend(np.round(p90, 2).tolist())
        columns["lgbm_point"].extend(np.round(lgbm, 2).tolist())
        columns["anomaly_score"].extend(np.round(anomaly, 4).tolist())
        columns["is_holiday"].extend(holiday_mask.tolist())
        columns["oil_event"].extend(oil_mask.tolist())

    return pd.DataFrame(columns)


def build_history(product_id: str, store_nbr: int, end_date: date, days: int = LOOKBACK_DAYS):
    """Historical actuals plus the model's back-cast for the same window."""
    rng = np.random.default_rng(_series_seed(product_id, store_nbr) + 7)
    base = float(np.random.default_rng(_series_seed(product_id, store_nbr)).uniform(12, 480))
    records = []
    for offset in range(days, 0, -1):
        day = end_date - timedelta(days=offset)
        seasonal = 1 + 0.18 * np.sin(2 * np.pi * (day.weekday() + 1) / 7)
        actual = max(0.0, base * seasonal * (1 + rng.normal(0, 0.12)))
        predicted = max(0.0, actual * (1 + rng.normal(0, 0.07)))
        records.append(
            {
                "date": day,
                "actual": round(actual, 2),
                "predicted": round(predicted, 2),
            }
        )
    return records


def build_attention(product_id: str, store_nbr: int, days: int = LOOKBACK_DAYS):
    """Decoder attention over the lookback window with peaks at lags 7/14/21/28."""
    rng = np.random.default_rng(_series_seed(product_id, store_nbr) + 13)
    lags = np.arange(1, days + 1)
    weights = 0.25 * np.exp(-lags / 45.0)
    for peak in ATTENTION_PEAKS:
        weights += 0.9 * np.exp(-((lags - peak) ** 2) / 3.0)
    weights += rng.uniform(0, 0.03, days)
    weights = weights / weights.sum()
    return [
        {"lag_days": int(lag), "weight": float(round(weight, 6))}
        for lag, weight in zip(lags, weights)
    ]


def build_metrics(weeks: int = 12) -> dict:
    """Weekly MAPE / coverage per model, most recent week last."""
    rng = np.random.default_rng(20240101)
    today = date.today()
    week_starts = [today - timedelta(days=7 * (weeks - i) + today.weekday()) for i in range(weeks)]
    baselines = {
        "TFT": 11.4,
        "LightGBM": 13.8,
        "ARIMA": 19.6,
        "Chronos-Bolt-Base 2024": 15.1,
    }
    weekly = []
    for index, week_start in enumerate(week_starts):
        drift = 0.18 * index
        entry = {"week_start": week_start.isoformat(), "models": {}}
        for model, baseline in baselines.items():
            mape = baseline + drift + float(rng.normal(0, 0.45))
            coverage = 0.80 + float(rng.normal(0, 0.02)) - (0.004 * index if model == "TFT" else 0)
            entry["models"][model] = {
                "mape": round(mape, 2),
                "coverage_rate": round(min(max(coverage, 0.5), 0.99), 4),
            }
        weekly.append(entry)
    return {
        "primary_model": "TFT",
        "coverage_target": 0.80,
        "weekly": weekly,
        "series_count": N_SERIES,
        "feature_count": 11,
    }


def build_feature_params() -> dict:
    """Stand-ins for oil_scaler.pkl / tsd_params.pkl feature-engineering params."""
    return {
        "oil_scaler": {"mean": 68.4, "scale": 12.7, "type": "StandardScaler"},
        "tsd_params": {
            "seasonal_period": 7,
            "trend_window": 28,
            "features": [
                "lag_1",
                "lag_7",
                "lag_14",
                "lag_28",
                "rolling_mean_7",
                "rolling_std_7",
                "rolling_mean_28",
                "oil_price_scaled",
                "is_holiday",
                "day_of_week",
                "anomaly_score",
            ],
        },
    }
