from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ConfidenceMode(str, Enum):
    LEAN = "lean"
    BALANCED = "balanced"
    SAFE = "safe"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InventoryRow(BaseModel):
    product_id: str
    store_nbr: int
    family: str
    current_stock: float
    p10: float
    p50: float
    p90: float
    base_quantity: float
    safety_buffer: float
    recommended_qty: float
    confidence_mode: ConfidenceMode
    anomaly_score: float
    risk_level: RiskLevel


class InventoryResponse(BaseModel):
    confidence_mode: ConfidenceMode
    rows: list[InventoryRow]
    total_units: float
    generated_at: datetime
    data_source: str


class OverrideCreate(BaseModel):
    product_id: str
    store_nbr: int = Field(ge=1, le=54)
    recommended_qty: float = Field(ge=0)
    override_qty: float = Field(ge=0)
    reason_code: str = Field(min_length=2, max_length=64)
    note: str | None = Field(default=None, max_length=1000)
    confidence_mode: ConfidenceMode = ConfidenceMode.BALANCED


class OverrideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    product_id: str
    store_nbr: int
    recommended_qty: float
    override_qty: float
    reason_code: str
    note: str | None
    confidence_mode: str
    created_at: datetime


class ExportLine(BaseModel):
    product_id: str
    store_nbr: int
    family: str
    order_qty: float = Field(ge=0)
    unit_cost: float | None = Field(default=None, ge=0)


class ExportRequest(BaseModel):
    confidence_mode: ConfidenceMode = ConfidenceMode.BALANCED
    supplier_name: str = Field(default="Preferred Supplier", max_length=128)
    lines: list[ExportLine] = Field(min_length=1)
