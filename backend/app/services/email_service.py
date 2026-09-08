"""SMTP alerting for anomaly spikes and drift-triggered retraining recommendations."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(recipients: list[str], subject: str, body: str) -> bool:
    """Synchronous send used by Celery tasks. Returns False when alerting is off."""
    if not recipients:
        return False
    if not settings.alerts_enabled or not settings.smtp_host:
        logger.info("alerts disabled - would email %s: %s", recipients, subject)
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            if settings.smtp_starttls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
    except Exception as exc:  # noqa: BLE001 - alerting must not fail the batch
        logger.error("failed to send alert email: %s", exc)
        return False
    return True


def anomaly_alert_body(store_nbr: int, products: list[dict]) -> str:
    lines = [
        f"ForecastIQ detected {len(products)} high-anomaly products for store {store_nbr}.",
        "",
        "Product            Date         Anomaly   P50",
    ]
    for product in products:
        lines.append(
            f"{product['product_id']:<18} {product['forecast_date']}  "
            f"{product['anomaly_score']:.2f}      {product['p50']:.1f}"
        )
    lines += ["", "Review the Inventory Decision Engine before placing today's order."]
    return "\n".join(lines)


def drift_alert_body(message: str, delta_pp: float, weeks: int) -> str:
    return (
        "ForecastIQ model drift detector triggered.\n\n"
        f"{message}\n\n"
        f"Rolling MAPE delta: {delta_pp:+.2f} percentage points over {weeks} consecutive weeks.\n"
        "Recommendation: schedule a TFT retraining run against the latest sales history."
    )
