from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ManagerOverride(Base):
    """Audit trail of manual order-quantity changes, used for model recalibration."""

    __tablename__ = "manager_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    product_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    store_nbr: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    recommended_qty: Mapped[float] = mapped_column(Float, nullable=False)
    override_qty: Mapped[float] = mapped_column(Float, nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="balanced")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    store_nbr: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    confidence_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_units: Mapped[float] = mapped_column(Float, nullable=False)
    export_format: Mapped[str] = mapped_column(String(8), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
