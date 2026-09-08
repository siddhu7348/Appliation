from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email.lower()))
    return result.scalar_one_or_none()


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(session, email)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role.value,
        store_nbr=payload.store_nbr,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def managers_for_store(session: AsyncSession, store_nbr: int) -> list[User]:
    result = await session.execute(
        select(User).where(User.store_nbr == store_nbr, User.is_active.is_(True))
    )
    return list(result.scalars().all())
