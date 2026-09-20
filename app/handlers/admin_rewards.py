from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import RewardStatus
from app.keyboards import AdminCB
from app.keyboards.admin import admin_rewards_list_keyboard
from app.repositories import rewards as rewards_repo
from app.services import rewards as rewards_service
from app.services import users as users_service
from app.services.notifications import notify_user
from app.utils.pagination import clamp_page, total_pages
from app.utils.telegram import IsAdmin, safe_edit
from app.utils.text import author_display, format_datetime, reward_status_label

logger = logging.getLogger(__name__)

router = Router(name="admin_rewards")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PER_PAGE = 5
FILTERS: dict[str, RewardStatus | None] = {
    "all": None,
    "pending": RewardStatus.PENDING,
    "manual": RewardStatus.MANUAL,
    "completed": RewardStatus.COMPLETED,
    "failed": RewardStatus.FAILED,
}


async def _render_list(
    callback: CallbackQuery,
    session: AsyncSession,
    *,
    status_filter: str,
    page: int,
) -> None:
    if status_filter not in FILTERS:
        status_filter = "all"
    status = FILTERS[status_filter]

    total = await rewards_repo.count(session, status=status)
    total_pages_count = total_pages(total, PER_PAGE)
    page = clamp_page(page, total, PER_PAGE)
    rewards = list(
        await rewards_repo.list_paginated(
            session, status=status, offset=page * PER_PAGE, limit=PER_PAGE
        )
    )

    title = "⭐ НАГРАДЫ"
    if not rewards:
        text = f"{title}\n\nВ этом разделе наград пока нет."
    else:
        lines = [
            title,
            "",
            f"Всего: {total}",
            f"Страница {page + 1} из {total_pages_count}",
            "",
        ]
        for reward in rewards:
            idea_number = (
                f"#{reward.idea.public_number}" if reward.idea else f"ID {reward.idea_id}"
            )
            admin_display = author_display(reward.admin) if reward.admin else "—"
            lines += [
                f"⭐ Награда #{reward.id}",
                f"💡 Идея {idea_number}",
                f"👤 Автор: {author_display(reward.user)}",
                f"🛡 Админ: {admin_display}",
                f"💵 Сумма: {reward.amount} {reward.currency.value}",
                f"📊 Статус: {reward_status_label(reward.status)}",
                f"🔗 Tx: {reward.telegram_transaction_id or '—'}",
                f"📅 {format_datetime(reward.created_at)}",
                "",
            ]
        text = "\n".join(lines)

    markup = admin_rewards_list_keyboard(
        rewards,
        status_filter=status_filter,
        page=page,
        total_pages_count=total_pages_count,
    )
    await safe_edit(callback, text, markup)


@router.callback_query(AdminCB.filter(F.action == "rewards"))
async def cb_rewards(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    await _render_list(
        callback,
        session,
        status_filter=callback_data.code or "all",
        page=callback_data.page,
    )
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "reward_done"))
async def cb_reward_done(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    reward = await rewards_repo.get_by_id(session, callback_data.entity_id)
    if reward is None:
        await callback.answer("Награда не найдена.", show_alert=True)
        return

    admin_user = await users_service.get_current_user(session, callback.from_user)
    outcome = await rewards_service.complete_manual_reward(
        session, reward=reward, admin_user=admin_user
    )
    await session.commit()

    if outcome.status == "duplicate":
        await callback.answer(outcome.admin_message, show_alert=True)
    else:
        if outcome.user_message and reward.user is not None:
            await notify_user(
                callback.bot,
                session,
                reward.user.telegram_id,
                outcome.user_message,
                force=True,
            )
        await callback.answer("Награда отмечена выполненной")

    await _render_list(
        callback,
        session,
        status_filter=callback_data.code or "all",
        page=callback_data.page,
    )
