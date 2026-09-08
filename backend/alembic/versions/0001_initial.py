"""initial schema

Revision ID: 0001
Revises:
Create Date: 2024-01-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("store_nbr", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "forecast_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("store_nbr", sa.Integer(), nullable=False),
        sa.Column("family", sa.String(length=64), nullable=False),
        sa.Column("forecast_date", sa.Date(), nullable=False),
        sa.Column("p10", sa.Float(), nullable=False),
        sa.Column("p50", sa.Float(), nullable=False),
        sa.Column("p90", sa.Float(), nullable=False),
        sa.Column("lgbm_point", sa.Float(), nullable=True),
        sa.Column("anomaly_score", sa.Float(), nullable=False),
        sa.Column("is_holiday", sa.Boolean(), nullable=False),
        sa.Column("oil_event", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_forecast_records_product_id", "forecast_records", ["product_id"])
    op.create_index("ix_forecast_records_store_nbr", "forecast_records", ["store_nbr"])
    op.create_index("ix_forecast_records_family", "forecast_records", ["family"])
    op.create_index(
        "ix_forecast_series_date",
        "forecast_records",
        ["product_id", "store_nbr", "forecast_date"],
        unique=True,
    )

    op.create_table(
        "manager_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_id", sa.String(length=64), nullable=False),
        sa.Column("store_nbr", sa.Integer(), nullable=False),
        sa.Column("recommended_qty", sa.Float(), nullable=False),
        sa.Column("override_qty", sa.Float(), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("confidence_mode", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_manager_overrides_user_id", "manager_overrides", ["user_id"])
    op.create_index("ix_manager_overrides_product_id", "manager_overrides", ["product_id"])
    op.create_index("ix_manager_overrides_store_nbr", "manager_overrides", ["store_nbr"])

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("store_nbr", sa.Integer(), nullable=False),
        sa.Column("confidence_mode", sa.String(length=16), nullable=False),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("total_units", sa.Float(), nullable=False),
        sa.Column("export_format", sa.String(length=8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_purchase_orders_user_id", "purchase_orders", ["user_id"])
    op.create_index("ix_purchase_orders_store_nbr", "purchase_orders", ["store_nbr"])

    op.create_table(
        "model_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("mape", sa.Float(), nullable=False),
        sa.Column("coverage_rate", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_model_metrics_week_start", "model_metrics", ["week_start"])
    op.create_index("ix_model_metrics_model_name", "model_metrics", ["model_name"])

    op.create_table(
        "drift_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mape_delta_pp", sa.Float(), nullable=False),
        sa.Column("consecutive_weeks", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("drift_events")
    op.drop_table("model_metrics")
    op.drop_table("purchase_orders")
    op.drop_table("manager_overrides")
    op.drop_table("forecast_records")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
