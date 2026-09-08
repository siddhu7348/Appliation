"""Smart-order recommendation engine and manager override audit trail."""

from __future__ import annotations

import zlib
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.artifacts import get_store
from app.models.inventory import ManagerOverride
from app.schemas.inventory import (
    ConfidenceMode,
    InventoryResponse,
    InventoryRow,
    OverrideCreate,
    RiskLevel,
)

SAFETY_BUFFER_RATIO = 0.15
HIGH_ANOMALY = settings.anomaly_alert_threshold


def _current_stock(product_id: str, store_nbr: int, p50: float) -> float:
    """Deterministic stand-in for the WMS on-hand feed."""
    fraction = 0.35 + (zlib.crc32(f"{product_id}|{store_nbr}|stock".encode()) % 60) / 100
    return round(p50 * fraction, 2)


def _risk_level(anomaly_score: float) -> RiskLevel:
    if anomaly_score >= HIGH_ANOMALY:
        return RiskLevel.HIGH
    if anomaly_score >= settings.anomaly_flag_threshold:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _base_quantity(mode: ConfidenceMode, p10: float, p50: float, p90: float) -> float:
    if mode is ConfidenceMode.LEAN:
        return p50
    if mode is ConfidenceMode.SAFE:
        return p90
    return p50 + 0.5 * (p90 - p50)  # Balanced == P75


def recommend_quantity(
    mode: ConfidenceMode,
    p10: float,
    p50: float,
    p90: float,
    current_stock: float,
    anomaly_score: float,
) -> tuple[float, float, float]:
    """Returns (base_quantity, safety_buffer, recommended_qty).

    High anomaly risk orders against P90 plus a safety buffer; stable series order
    against the confidence-mode base only.
    """
    high_risk = anomaly_score >= HIGH_ANOMALY
    base = p90 if high_risk else _base_quantity(mode, p10, p50, p90)
    buffer = round(p90 * SAFETY_BUFFER_RATIO, 2) if high_risk else 0.0
    recommended = max(0.0, round(base - current_stock + buffer, 2))
    return round(base, 2), buffer, recommended


def build_recommendations(
    mode: ConfidenceMode,
    store_nbr: int | None = None,
    family: str | None = None,
    limit: int = 200,
) -> InventoryResponse:
    artifacts = get_store()
    frame: pd.DataFrame = artifacts.forecasts
    horizon_start = frame["forecast_date"].min()
    frame = frame[frame["forecast_date"] == horizon_start]
    if store_nbr is not None:
        frame = frame[frame["store_nbr"] == store_nbr]
    if family:
        frame = frame[frame["family"] == family]
    frame = frame.sort_values("p50", ascending=False).head(limit)

    rows: list[InventoryRow] = []
    for record in frame.itertuples(index=False):
        p10, p50, p90 = float(record.p10), float(record.p50), float(record.p90)
        stock = _current_stock(str(record.product_id), int(record.store_nbr), p50)
        anomaly = float(record.anomaly_score)
        base, buffer, recommended = recommend_quantity(mode, p10, p50, p90, stock, anomaly)
        rows.append(
            InventoryRow(
                product_id=str(record.product_id),
                store_nbr=int(record.store_nbr),
                family=str(record.family),
                current_stock=stock,
                p10=p10,
                p50=p50,
                p90=p90,
                base_quantity=base,
                safety_buffer=buffer,
                recommended_qty=recommended,
                confidence_mode=mode,
                anomaly_score=anomaly,
                risk_level=_risk_level(anomaly),
            )
        )

    return InventoryResponse(
        confidence_mode=mode,
        rows=rows,
        total_units=round(sum(row.recommended_qty for row in rows), 2),
        generated_at=datetime.now(timezone.utc),
        data_source="synthetic" if artifacts.is_synthetic else "artifacts",
    )


async def log_override(
    session: AsyncSession, user_id: int, payload: OverrideCreate
) -> ManagerOverride:
    override = ManagerOverride(
        user_id=user_id,
        product_id=payload.product_id,
        store_nbr=payload.store_nbr,
        recommended_qty=payload.recommended_qty,
        override_qty=payload.override_qty,
        reason_code=payload.reason_code,
        note=payload.note,
        confidence_mode=payload.confidence_mode.value,
    )
    session.add(override)
    await session.commit()
    await session.refresh(override)
    return override


async def list_overrides(
    session: AsyncSession, store_nbr: int | None = None, limit: int = 100
) -> list[ManagerOverride]:
    statement = select(ManagerOverride).order_by(ManagerOverride.created_at.desc()).limit(limit)
    if store_nbr is not None:
        statement = statement.where(ManagerOverride.store_nbr == store_nbr)
    result = await session.execute(statement)
    return list(result.scalars().all())
