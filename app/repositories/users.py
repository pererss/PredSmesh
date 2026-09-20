from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utcnow
from app.database.models import Idea, Referral, Reward, User


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def get_by_id(session: AsyncSession, user_id: int) -> User | None:
    return await session.get(User, user_id)


async def get_or_create(
    session: AsyncSession,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
) -> User:
    user = await get_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            last_activity=utcnow(),
        )
        session.add(user)
        try:
            async with session.begin_nested():
                await session.flush()
        except IntegrityError:
            user = await get_by_telegram_id(session, telegram_id)
            if user is None:
                raise
    user.username = username
    user.first_name = first_name
    user.last_name = last_name
    user.last_activity = utcnow()
    if not user.is_active:
        user.is_active = True
    return user


async def set_active(session: AsyncSession, user: User, is_active: bool) -> None:
    user.is_active = is_active
    await session.flush()


async def set_active_by_telegram_id(
    session: AsyncSession, telegram_id: int, is_active: bool
) -> None:
    user = await get_by_telegram_id(session, telegram_id)
    if user is not None:
        user.is_active = is_active
        await session.flush()


async def list_paginated(
    session: AsyncSession, *, offset: int, limit: int
) -> Sequence[User]:
    result = await session.scalars(
        select(User).order_by(User.created_at.desc(), User.id.desc()).offset(offset).limit(limit)
    )
    return result.all()


async def list_active_paginated(
    session: AsyncSession, *, offset: int, limit: int
) -> Sequence[User]:
    result = await session.scalars(
        select(User)
        .where(User.is_active.is_(True))
        .order_by(User.id)
        .offset(offset)
        .limit(limit)
    )
    return result.all()


async def count_all(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(User)) or 0)


async def count_active(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        )
        or 0
    )


async def count_created_since(session: AsyncSession, since: datetime) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.created_at >= since)
        )
        or 0
    )


async def count_ideas(session: AsyncSession, user_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Idea).where(Idea.user_id == user_id)
        )
        or 0
    )


async def count_rewards(session: AsyncSession, user_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Reward).where(Reward.user_id == user_id)
        )
        or 0
    )


async def count_referrals(session: AsyncSession, referrer_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Referral)
            .where(Referral.referrer_id == referrer_id)
        )
        or 0
    )


async def count_all_referrals(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(Referral)) or 0)


async def create_referral(
    session: AsyncSession, *, referrer_id: int, referred_id: int
) -> bool:
    try:
        async with session.begin_nested():
            session.add(Referral(referrer_id=referrer_id, referred_id=referred_id))
            await session.flush()
    except IntegrityError:
        return False
    return True
