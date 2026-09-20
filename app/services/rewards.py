from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utcnow
from app.database.models import Idea, IdeaStatus, Reward, RewardStatus, User
from app.repositories import rewards as rewards_repo
from app.services import admin as admin_log

try:  # Bot API 8.0+ only
    from aiogram.methods import SendGift
except ImportError:  # pragma: no cover - older aiogram versions
    SendGift = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

MANUAL_REWARD_NOTE = (
    "⚠️ Награда сохранена со статусом MANUAL и требует ручной обработки.\n\n"
    "Telegram Bot API не позволяет боту напрямую перевести Stars пользователю. "
    "Отправь награду вручную, затем отметь её выполненной в разделе «⭐ Награды»."
)


@dataclass(slots=True)
class RewardOutcome:
    status: str
    reward: Reward
    admin_message: str
    user_message: str | None = None


async def grant_reward(
    session: AsyncSession,
    *,
    bot: Bot,
    idea: Idea,
    admin_user: User,
    amount: int,
    gift_id: str | None = None,
) -> RewardOutcome:
    existing = await rewards_repo.get_active_for_idea(session, idea.id)
    if existing is not None:
        return RewardOutcome(
            status="duplicate",
            reward=existing,
            admin_message=(
                f"Награда по идее #{idea.public_number} уже создана "
                f"(статус: {existing.status.value}). Повторная выплата не создаётся."
            ),
        )

    reward_status = RewardStatus.MANUAL
    admin_message = MANUAL_REWARD_NOTE
    user_message: str | None = None

    if gift_id and SendGift is not None and idea.author is not None:
        try:
            await bot(SendGift(user_id=idea.author.telegram_id, gift_id=gift_id))
        except TelegramAPIError as exc:
            logger.warning("sendGift failed for idea %s: %s", idea.id, exc)
            admin_message = (
                "⚠️ Отправить подарок через Telegram не удалось. "
                "Награда сохранена со статусом MANUAL и требует ручной обработки."
            )
        else:
            reward_status = RewardStatus.COMPLETED
            admin_message = (
                "✅ Подарок отправлен автору. Награда отмечена как COMPLETED."
            )
            user_message = (
                f"🎁 Награда по идее #{idea.public_number} обработана — "
                "тебе отправлен подарок от Telegram."
            )

    reward = await rewards_repo.create(
        session,
        idea_id=idea.id,
        user_id=idea.user_id,
        admin_id=admin_user.id,
        amount=amount,
        status=reward_status,
    )
    if reward_status == RewardStatus.COMPLETED:
        idea.status = IdeaStatus.REWARDED
        idea.rewarded_at = utcnow()

    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="reward" if reward_status == RewardStatus.COMPLETED else "manual_reward",
        idea_id=idea.id,
        target_user_id=idea.user_id,
        details=(
            f"Награда {amount} XTR по идее #{idea.public_number}: "
            f"{reward_status.value}"
        ),
    )
    await session.flush()
    return RewardOutcome(
        status="completed" if reward_status == RewardStatus.COMPLETED else "manual",
        reward=reward,
        admin_message=admin_message,
        user_message=user_message,
    )


async def complete_manual_reward(
    session: AsyncSession, *, reward: Reward, admin_user: User
) -> RewardOutcome:
    if reward.status == RewardStatus.COMPLETED:
        return RewardOutcome(
            status="duplicate",
            reward=reward,
            admin_message="Эта награда уже отмечена выполненной.",
        )

    reward.status = RewardStatus.COMPLETED
    idea = reward.idea
    if idea is not None:
        idea.status = IdeaStatus.REWARDED
        idea.rewarded_at = utcnow()

    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="reward_completed",
        idea_id=reward.idea_id,
        target_user_id=reward.user_id,
        details=(
            f"Награда #{reward.id} ({reward.amount} XTR) отмечена выполненной вручную"
        ),
    )
    await session.flush()
    user_message = (
        f"⭐ Награда {reward.amount} ⭐ по идее #{idea.public_number} обработана."
        if idea is not None
        else None
    )
    return RewardOutcome(
        status="completed",
        reward=reward,
        admin_message="✅ Награда отмечена выполненной.",
        user_message=user_message,
    )
