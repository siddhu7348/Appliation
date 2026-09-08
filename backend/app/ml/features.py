"""Feature engineering + anomaly scoring used by the nightly batch job."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURE_COLUMNS = [
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
    "promo_intensity",
]


def build_features(history: pd.DataFrame) -> pd.DataFrame:
    """Compute the 11 engineered features from a ``date``/``sales`` history frame."""
    frame = history.sort_values("date").copy()
    for lag in (1, 7, 14, 28):
        frame[f"lag_{lag}"] = frame["sales"].shift(lag)
    frame["rolling_mean_7"] = frame["sales"].shift(1).rolling(7).mean()
    frame["rolling_std_7"] = frame["sales"].shift(1).rolling(7).std()
    frame["rolling_mean_28"] = frame["sales"].shift(1).rolling(28).mean()
    if "oil_price" in frame.columns:
        oil = frame["oil_price"]
        frame["oil_price_scaled"] = (oil - oil.mean()) / (oil.std() or 1.0)
    else:
        frame["oil_price_scaled"] = 0.0
    if "is_holiday" not in frame.columns:
        frame["is_holiday"] = 0
    frame["is_holiday"] = frame["is_holiday"].astype(int)
    frame["day_of_week"] = pd.to_datetime(frame["date"]).dt.dayofweek
    if "promo_intensity" not in frame.columns:
        frame["promo_intensity"] = 0.0
    return frame[["date", *FEATURE_COLUMNS]].fillna(0.0)


def dynamic_contamination(features: pd.DataFrame, floor: float = 0.01, ceiling: float = 0.15):
    """CV-based contamination: noisier series get a higher outlier budget."""
    values = features["rolling_mean_7"].to_numpy(dtype=float)
    std = features["rolling_std_7"].to_numpy(dtype=float)
    mean = float(np.mean(values)) or 1.0
    cv = float(np.mean(std)) / abs(mean)
    return float(min(max(cv / 4, floor), ceiling))


def anomaly_scores(features: pd.DataFrame) -> np.ndarray:
    """IsolationForest scores rescaled to 0-1 where 1 is most anomalous."""
    matrix = features[FEATURE_COLUMNS].to_numpy(dtype=float)
    if matrix.shape[0] < 8:
        return np.zeros(matrix.shape[0])
    model = IsolationForest(
        n_estimators=120,
        contamination=dynamic_contamination(features),
        random_state=42,
    )
    model.fit(matrix)
    raw = -model.score_samples(matrix)
    spread = raw.max() - raw.min()
    if spread == 0:
        return np.zeros_like(raw)
    return (raw - raw.min()) / spread
