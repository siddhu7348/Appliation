"""Artifact loading with synthetic fallback.

The app never trains: it consumes the artifacts dropped into ``settings.artifacts_dir``
by the offline TFT pipeline. Any missing artifact is replaced by a realistic
synthetic equivalent so the stack always runs.
"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from threading import Lock
from typing import Any

import pandas as pd

from app.core.config import settings
from app.ml import synthetic

logger = logging.getLogger(__name__)

FORECAST_CSV = "forecast_readable.csv"
LGBM_PICKLE = "lgbm_model.pkl"
METRICS_PICKLE = "metrics.pkl"
OIL_SCALER_PICKLE = "oil_scaler.pkl"
TSD_PARAMS_PICKLE = "tsd_params.pkl"


@dataclass
class ArtifactStore:
    forecasts: pd.DataFrame
    metrics: dict[str, Any]
    feature_params: dict[str, Any]
    lgbm_model: Any = None
    sources: dict[str, str] = field(default_factory=dict)

    @property
    def is_synthetic(self) -> bool:
        return all(source == "synthetic" for source in self.sources.values())

    def catalog(self) -> pd.DataFrame:
        return (
            self.forecasts[["product_id", "store_nbr", "family"]]
            .drop_duplicates()
            .sort_values(["store_nbr", "product_id"])
            .reset_index(drop=True)
        )

    def series_forecast(self, product_id: str, store_nbr: int) -> pd.DataFrame:
        mask = (self.forecasts["product_id"] == product_id) & (
            self.forecasts["store_nbr"] == store_nbr
        )
        return self.forecasts[mask].sort_values("forecast_date")

    def history(self, product_id: str, store_nbr: int) -> list[dict[str, Any]]:
        start = self.forecasts["forecast_date"].min()
        return synthetic.build_history(product_id, store_nbr, start)

    def attention(self, product_id: str, store_nbr: int) -> list[dict[str, Any]]:
        return synthetic.build_attention(product_id, store_nbr)


_store: ArtifactStore | None = None
_lock = Lock()


def _load_pickle(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            return pickle.load(handle)
    except Exception as exc:  # noqa: BLE001 - a corrupt artifact must not block startup
        logger.warning("failed to load artifact %s: %s", path, exc)
        return None


def _load_forecast_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    try:
        frame = pd.read_csv(path, parse_dates=["forecast_date"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("failed to read %s: %s", path, exc)
        return None
    required = {"product_id", "store_nbr", "family", "forecast_date", "p10", "p50", "p90"}
    missing = required - set(frame.columns)
    if missing:
        logger.warning("%s missing columns %s - falling back to synthetic", path, sorted(missing))
        return None
    frame["forecast_date"] = frame["forecast_date"].dt.date
    for column, default in (("anomaly_score", 0.0), ("is_holiday", False), ("oil_event", False)):
        if column not in frame.columns:
            frame[column] = default
    if "lgbm_point" not in frame.columns:
        frame["lgbm_point"] = frame["p50"]
    frame["is_holiday"] = frame["is_holiday"].astype(bool)
    frame["oil_event"] = frame["oil_event"].astype(bool)
    return frame


def load_store(force_reload: bool = False) -> ArtifactStore:
    global _store
    with _lock:
        if _store is not None and not force_reload:
            return _store

        directory = Path(settings.artifacts_dir)
        sources: dict[str, str] = {}

        forecasts = _load_forecast_csv(directory / FORECAST_CSV)
        if forecasts is None:
            forecasts = synthetic.build_forecast_frame(date.today())
            sources["forecasts"] = "synthetic"
        else:
            sources["forecasts"] = "artifact"

        metrics = _load_pickle(directory / METRICS_PICKLE)
        if not isinstance(metrics, dict) or "weekly" not in metrics:
            metrics = synthetic.build_metrics()
            sources["metrics"] = "synthetic"
        else:
            sources["metrics"] = "artifact"

        lgbm_model = _load_pickle(directory / LGBM_PICKLE)
        sources["lgbm_model"] = "artifact" if lgbm_model is not None else "synthetic"

        oil_scaler = _load_pickle(directory / OIL_SCALER_PICKLE)
        tsd_params = _load_pickle(directory / TSD_PARAMS_PICKLE)
        if oil_scaler is None or tsd_params is None:
            feature_params = synthetic.build_feature_params()
            sources["feature_params"] = "synthetic"
        else:
            feature_params = {"oil_scaler": oil_scaler, "tsd_params": tsd_params}
            sources["feature_params"] = "artifact"

        _store = ArtifactStore(
            forecasts=forecasts,
            metrics=metrics,
            feature_params=feature_params,
            lgbm_model=lgbm_model,
            sources=sources,
        )
        logger.info("artifact store loaded: %s", sources)
        return _store


def get_store() -> ArtifactStore:
    return load_store()
