from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import AdminCB
from app.keyboards.admin import admin_back_keyboard, admin_menu_keyboard
from app.services import statistics as statistics_service
from app.utils.telegram import IsAdmin, safe_edit

logger = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

ADMIN_MENU_TEXT = "🛠 АДМИН-ПАНЕЛЬ\n\nВыбери раздел:"


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ADMIN_MENU_TEXT, reply_markup=admin_menu_keyboard())


@router.callback_query(AdminCB.filter(F.action == "panel"))
async def cb_panel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback, ADMIN_MENU_TEXT, admin_menu_keyboard())
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "stats"))
async def cb_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    global_stats = await statistics_service.collect_global(session)
    today_stats = await statistics_service.collect_today(session)
    text = (
        "📊 СТАТИСТИКА\n\n"
        f"👥 Пользователей: {global_stats.users_total}\n"
        f"✅ Активных: {global_stats.users_active}\n"
        f"💡 Всего идей: {global_stats.ideas_total}\n"
        f"📥 На рассмотрении: {global_stats.ideas_pending}\n"
        f"✅ Одобрено: {global_stats.ideas_approved}\n"
        f"❌ Отклонено: {global_stats.ideas_rejected}\n"
        f"⭐ Награждено: {global_stats.ideas_rewarded}\n"
        f"🔒 Скрыто: {global_stats.ideas_hidden}\n"
        f"❤️ Лайков: {global_stats.likes_total}\n"
        f"👁 Просмотров: {global_stats.views_total}\n"
        f"🎁 Приглашено пользователей: {global_stats.referrals_total}\n"
        f"⭐ Награды (выполнено / вручную): "
        f"{global_stats.rewards_completed} / {global_stats.rewards_manual}\n\n"
        "📅 За сегодня:\n"
        f"👥 Новых пользователей: {today_stats.users}\n"
        f"💡 Новых идей: {today_stats.ideas}\n"
        f"✅ Одобренных идей: {today_stats.approved}\n"
        f"❌ Отклонённых идей: {today_stats.rejected}\n"
        f"⭐ Наград: {today_stats.rewards}"
    )
    await safe_edit(callback, text, admin_back_keyboard())
    await callback.answer()
