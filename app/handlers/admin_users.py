from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import AdminCB
from app.keyboards.admin import (
    admin_user_card_keyboard,
    admin_users_list_keyboard,
)
from app.repositories import users as users_repo
from app.services.statistics import start_of_today
from app.utils.pagination import clamp_page, total_pages
from app.utils.telegram import IsAdmin, safe_edit
from app.utils.text import escape_html, format_datetime

logger = logging.getLogger(__name__)

router = Router(name="admin_users")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PER_PAGE = 8


@router.callback_query(AdminCB.filter(F.action == "users"))
async def cb_users(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    total = await users_repo.count_all(session)
    active = await users_repo.count_active(session)
    new_today = await users_repo.count_created_since(session, start_of_today())

    total_pages_count = total_pages(total, PER_PAGE)
    page = clamp_page(callback_data.page, total, PER_PAGE)
    users = await users_repo.list_paginated(
        session, offset=page * PER_PAGE, limit=PER_PAGE
    )

    header = (
        "👥 ПОЛЬЗОВАТЕЛИ\n\n"
        f"Всего: {total}\n"
        f"✅ Активных: {active}\n"
        f"🆕 Новых за сегодня: {new_today}"
    )
    if not users:
        text = f"{header}\n\nПользователей пока нет."
    else:
        text = f"{header}\n\nСтраница {page + 1} из {total_pages_count}"

    markup = admin_users_list_keyboard(
        list(users), page=page, total_pages_count=total_pages_count
    )
    await safe_edit(callback, text, markup)
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "user"))
async def cb_user(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    user = await users_repo.get_by_id(session, callback_data.entity_id)
    if user is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return

    ideas_count = await users_repo.count_ideas(session, user.id)
    rewards_count = await users_repo.count_rewards(session, user.id)
    referrals_count = await users_repo.count_referrals(session, user.id)

    username = f"@{user.username}" if user.username else "—"
    text = (
        "👤 ПОЛЬЗОВАТЕЛЬ\n\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Username: {escape_html(username)}\n"
        f"Имя: {escape_html(user.first_name or '—')}\n"
        f"Регистрация: {format_datetime(user.created_at)}\n"
        f"Последняя активность: {format_datetime(user.last_activity)}\n"
        f"Активен: {'✅' if user.is_active else '⛔'}\n\n"
        f"💡 Идей: {ideas_count}\n"
        f"⭐ Наград: {rewards_count}\n"
        f"🎁 Рефералов: {referrals_count}"
    )
    await safe_edit(callback, text, admin_user_card_keyboard(callback_data.page))
    await callback.answer()
