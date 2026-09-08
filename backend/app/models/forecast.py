from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ForecastRecord(Base):
    """Nightly batch output: one row per product-store-horizon day."""

    __tablename__ = "forecast_records"
    __table_args__ = (
        Index("ix_forecast_series_date", "product_id", "store_nbr", "forecast_date", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    store_nbr: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    family: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    p10: Mapped[float] = mapped_column(Float, nullable=False)
    p50: Mapped[float] = mapped_column(Float, nullable=False)
    p90: Mapped[float] = mapped_column(Float, nullable=False)
    lgbm_point: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_holiday: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    oil_event: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
