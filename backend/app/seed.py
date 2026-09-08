"""Seed demo users, one per role. Idempotent: existing emails are skipped.

Usage: ``python -m app.seed``
"""

from __future__ import annotations

import asyncio
import logging
import os

from app.core.db import AsyncSessionLocal, Base, engine
from app.models.user import UserRole
from app.schemas.auth import UserCreate
from app.services.auth_service import create_user, get_user_by_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_PASSWORD = os.getenv("SEED_DEMO_PASSWORD", "ForecastIQ!2024")

DEMO_USERS = [
    UserCreate(
        email="manager@forecastiq.io",
        full_name="Sofia Reyes",
        password=DEFAULT_PASSWORD,
        role=UserRole.STORE_MANAGER,
        store_nbr=1,
    ),
    UserCreate(
        email="director@forecastiq.io",
        full_name="Marco Vela",
        password=DEFAULT_PASSWORD,
        role=UserRole.REGIONAL_DIRECTOR,
        store_nbr=None,
    ),
    UserCreate(
        email="hq@forecastiq.io",
        full_name="Ana Castillo",
        password=DEFAULT_PASSWORD,
        role=UserRole.HQ,
        store_nbr=None,
    ),
    UserCreate(
        email="admin@forecastiq.io",
        full_name="Diego Paredes",
        password=DEFAULT_PASSWORD,
        role=UserRole.ADMIN,
        store_nbr=None,
    ),
]


async def seed() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        for payload in DEMO_USERS:
            if await get_user_by_email(session, payload.email):
                logger.info("user already exists: %s", payload.email)
                continue
            await create_user(session, payload)
            logger.info("created %s (%s)", payload.email, payload.role.value)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
