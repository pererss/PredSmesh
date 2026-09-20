from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import AdminCB
from app.keyboards.admin import (
    admin_back_keyboard,
    admin_cancel_keyboard,
    admin_user_card_keyboard,
    admin_users_list_keyboard,
)
from app.repositories import users as users_repo
from app.services import admin as admin_log
from app.services import users as users_service
from app.services.notifications import notify_user
from app.services.statistics import start_of_today
from app.states.admin import AdminUserMessageForm
from app.utils.pagination import clamp_page, total_pages
from app.utils.telegram import IsAdmin, safe_edit
from app.utils.text import author_display, escape_html, format_datetime

logger = logging.getLogger(__name__)

router = Router(name="admin_users")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PER_PAGE = 8


async def build_user_card(
    session: AsyncSession, user, page: int
) -> tuple[str, InlineKeyboardMarkup]:
    ideas_count = await users_repo.count_ideas(session, user.id)
    rewards_count = await users_repo.count_rewards(session, user.id)
    referrals_count = await users_repo.count_referrals(session, user.id)
    username = f"@{user.username}" if user.username else "—"
    status = "✅ активен" if user.is_active else "🚫 заблокирован"
    text = (
        "👤 ПОЛЬЗОВАТЕЛЬ\n\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Username: {escape_html(username)}\n"
        f"Имя: {escape_html(user.first_name or '—')}\n"
        f"Статус: {status}\n"
        f"Регистрация: {format_datetime(user.created_at)}\n"
        f"Последняя активность: {format_datetime(user.last_activity)}\n\n"
        f"💡 Идей: {ideas_count}\n"
        f"⭐ Наград: {rewards_count}\n"
        f"🎁 Рефералов: {referrals_count}"
    )
    markup = admin_user_card_keyboard(
        user.id, is_active=user.is_active, page=page
    )
    return text, markup


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
    text, markup = await build_user_card(session, user, callback_data.page)
    await safe_edit(callback, text, markup)
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "ban"))
async def cb_ban(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    user = await users_repo.get_by_id(session, callback_data.entity_id)
    if user is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    new_state = not user.is_active
    await users_repo.set_active(session, user, new_state)
    admin_user = await users_service.get_current_user(session, callback.from_user)
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="unban_user" if new_state else "ban_user",
        target_user_id=user.id,
        details=(
            f"Пользователь {user.telegram_id} "
            f"{'разблокирован' if new_state else 'заблокирован'}"
        ),
    )
    await session.commit()
    text, markup = await build_user_card(session, user, callback_data.page)
    await safe_edit(callback, text, markup)
    await callback.answer(
        "Пользователь разблокирован" if new_state else "Пользователь заблокирован"
    )


@router.callback_query(AdminCB.filter(F.action == "reply_user"))
async def cb_reply_user(
    callback: CallbackQuery,
    callback_data: AdminCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await users_repo.get_by_id(session, callback_data.entity_id)
    if user is None:
        await callback.answer("Пользователь не найден.", show_alert=True)
        return
    await state.set_state(AdminUserMessageForm.waiting_for_text)
    await state.update_data(target_user_id=user.id, page=callback_data.page)
    await safe_edit(
        callback,
        (
            f"💬 Напиши сообщение пользователю {author_display(user)}.\n\n"
            "Оно будет отправлено от имени администрации."
        ),
        admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminUserMessageForm.waiting_for_text, F.text)
async def process_user_message(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    user = await users_repo.get_by_id(session, int(data.get("target_user_id", 0)))
    if user is None:
        await state.clear()
        await message.answer("Пользователь не найден.", reply_markup=admin_back_keyboard())
        return

    text_value = (message.text or "").strip()
    admin_user = await users_service.get_current_user(session, message.from_user)
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="message_user",
        target_user_id=user.id,
        details=text_value[:500],
    )
    await session.commit()

    sent = await notify_user(
        message.bot,
        session,
        user.telegram_id,
        f"💬 Сообщение от администрации:\n\n{escape_html(text_value)}",
        force=True,
    )
    await state.clear()
    note = (
        "✅ Сообщение отправлено."
        if sent
        else "⚠️ Не удалось отправить (пользователь мог заблокировать бота)."
    )
    await message.answer(
        note,
        reply_markup=admin_user_card_keyboard(
            user.id, is_active=user.is_active, page=int(data.get("page", 0))
        ),
    )


@router.message(AdminUserMessageForm.waiting_for_text)
async def process_user_message_non_text(message: Message) -> None:
    await message.answer("Отправь сообщение текстом.")
