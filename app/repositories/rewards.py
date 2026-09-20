from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Reward, RewardCurrency, RewardStatus

ACTIVE_STATUSES = (
    RewardStatus.PENDING,
    RewardStatus.COMPLETED,
    RewardStatus.MANUAL,
)


async def create(
    session: AsyncSession,
    *,
    idea_id: int,
    user_id: int,
    admin_id: int | None,
    amount: int,
    status: RewardStatus,
    currency: RewardCurrency = RewardCurrency.XTR,
    telegram_transaction_id: str | None = None,
) -> Reward:
    reward = Reward(
        idea_id=idea_id,
        user_id=user_id,
        admin_id=admin_id,
        amount=amount,
        status=status,
        currency=currency,
        telegram_transaction_id=telegram_transaction_id,
    )
    session.add(reward)
    await session.flush()
    return reward


async def get_by_id(session: AsyncSession, reward_id: int) -> Reward | None:
    return await session.get(Reward, reward_id)


async def get_active_for_idea(session: AsyncSession, idea_id: int) -> Reward | None:
    return await session.scalar(
        select(Reward)
        .where(Reward.idea_id == idea_id, Reward.status.in_(ACTIVE_STATUSES))
        .order_by(Reward.id.desc())
        .limit(1)
    )


async def list_paginated(
    session: AsyncSession,
    *,
    status: RewardStatus | None,
    offset: int,
    limit: int,
) -> Sequence[Reward]:
    stmt = select(Reward)
    if status is not None:
        stmt = stmt.where(Reward.status == status)
    result = await session.scalars(
        stmt.order_by(Reward.created_at.desc(), Reward.id.desc()).offset(offset).limit(limit)
    )
    return result.all()


async def count(session: AsyncSession, *, status: RewardStatus | None) -> int:
    stmt = select(func.count()).select_from(Reward)
    if status is not None:
        stmt = stmt.where(Reward.status == status)
    return int(await session.scalar(stmt) or 0)


async def count_completed_since(session: AsyncSession, since: datetime) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Reward)
            .where(Reward.status == RewardStatus.COMPLETED, Reward.created_at >= since)
        )
        or 0
    )


async def count_created_since(session: AsyncSession, since: datetime) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Reward).where(Reward.created_at >= since)
        )
        or 0
    )


async def count_for_user(session: AsyncSession, user_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Reward).where(Reward.user_id == user_id)
        )
        or 0
    )
