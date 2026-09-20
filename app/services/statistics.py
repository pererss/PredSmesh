from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Idea,
    IdeaStatus,
    Like,
    Referral,
    Reward,
    RewardStatus,
    User,
)


def start_of_today() -> datetime:
    now = datetime.now(timezone.utc)
    return datetime.combine(now.date(), time.min, tzinfo=timezone.utc)


@dataclass(slots=True)
class GlobalStats:
    users_total: int
    users_active: int
    ideas_total: int
    ideas_pending: int
    ideas_approved: int
    ideas_rejected: int
    ideas_rewarded: int
    ideas_hidden: int
    likes_total: int
    views_total: int
    referrals_total: int
    rewards_completed: int
    rewards_manual: int


@dataclass(slots=True)
class TodayStats:
    users: int
    ideas: int
    approved: int
    rejected: int
    rewards: int


async def collect_global(session: AsyncSession) -> GlobalStats:
    status_rows = await session.execute(
        select(Idea.status, func.count()).group_by(Idea.status)
    )
    by_status = {status: int(count) for status, count in status_rows.all()}

    users_total = int(await session.scalar(select(func.count()).select_from(User)) or 0)
    users_active = int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.is_active.is_(True))
        )
        or 0
    )
    likes_total = int(await session.scalar(select(func.count()).select_from(Like)) or 0)
    views_total = int(
        await session.scalar(select(func.coalesce(func.sum(Idea.views_count), 0))) or 0
    )
    referrals_total = int(
        await session.scalar(select(func.count()).select_from(Referral)) or 0
    )
    rewards_completed = int(
        await session.scalar(
            select(func.count())
            .select_from(Reward)
            .where(Reward.status == RewardStatus.COMPLETED)
        )
        or 0
    )
    rewards_manual = int(
        await session.scalar(
            select(func.count())
            .select_from(Reward)
            .where(Reward.status == RewardStatus.MANUAL)
        )
        or 0
    )

    return GlobalStats(
        users_total=users_total,
        users_active=users_active,
        ideas_total=sum(by_status.values()),
        ideas_pending=by_status.get(IdeaStatus.PENDING, 0),
        ideas_approved=by_status.get(IdeaStatus.APPROVED, 0),
        ideas_rejected=by_status.get(IdeaStatus.REJECTED, 0),
        ideas_rewarded=by_status.get(IdeaStatus.REWARDED, 0),
        ideas_hidden=by_status.get(IdeaStatus.HIDDEN, 0),
        likes_total=likes_total,
        views_total=views_total,
        referrals_total=referrals_total,
        rewards_completed=rewards_completed,
        rewards_manual=rewards_manual,
    )


async def collect_today(session: AsyncSession) -> TodayStats:
    since = start_of_today()
    users = int(
        await session.scalar(
            select(func.count()).select_from(User).where(User.created_at >= since)
        )
        or 0
    )
    ideas = int(
        await session.scalar(
            select(func.count()).select_from(Idea).where(Idea.created_at >= since)
        )
        or 0
    )
    approved = int(
        await session.scalar(
            select(func.count())
            .select_from(Idea)
            .where(Idea.approved_at.is_not(None), Idea.approved_at >= since)
        )
        or 0
    )
    rejected = int(
        await session.scalar(
            select(func.count())
            .select_from(Idea)
            .where(Idea.status == IdeaStatus.REJECTED, Idea.updated_at >= since)
        )
        or 0
    )
    rewards = int(
        await session.scalar(
            select(func.count()).select_from(Reward).where(Reward.created_at >= since)
        )
        or 0
    )
    return TodayStats(
        users=users, ideas=ideas, approved=approved, rejected=rejected, rewards=rewards
    )
