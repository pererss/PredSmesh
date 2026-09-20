from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import AdminCB
from app.keyboards.admin import (
    admin_back_keyboard,
    admin_cancel_keyboard,
    admin_settings_keyboard,
)
from app.services import admin as admin_log
from app.services import settings as settings_service
from app.services import users as users_service
from app.states.admin import SettingsForm
from app.utils.telegram import IsAdmin, safe_edit
from app.utils.text import parse_bool

logger = logging.getLogger(__name__)

router = Router(name="admin_settings")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

EDITABLE_KEYS = {"reward_amount", "reward_gift_id"}
TOGGLE_KEYS = {"submissions_enabled", "notifications_enabled"}


async def _render_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    values = await settings_service.get_all(session)
    submissions = "включён" if parse_bool(values.get("submissions_enabled"), True) else "выключен"
    notifications = (
        "включены" if parse_bool(values.get("notifications_enabled"), True) else "выключены"
    )
    text = (
        "⚙️ НАСТРОЙКИ\n\n"
        f"💰 Награда: {values.get('reward_amount', '15')} ⭐\n"
        f"📥 Приём идей: {submissions}\n"
        f"🔔 Уведомления: {notifications}\n"
        f"🎁 Gift ID: {values.get('reward_gift_id') or '—'}\n\n"
        "Значения хранятся в таблице settings."
    )
    await safe_edit(callback, text, admin_settings_keyboard(values))


@router.callback_query(AdminCB.filter(F.action == "settings"))
async def cb_settings(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await _render_settings(callback, session)
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "setting_toggle"))
async def cb_setting_toggle(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    key = callback_data.code
    if key not in TOGGLE_KEYS:
        await callback.answer("Эту настройку нельзя переключить.", show_alert=True)
        return
    current = await settings_service.get_bool(session, key, True)
    new_value = "false" if current else "true"
    await settings_service.set_value(session, key, new_value)

    admin_user = await users_service.get_current_user(session, callback.from_user)
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="settings_change",
        details=f"{key} = {new_value}",
    )
    await session.commit()
    await _render_settings(callback, session)
    await callback.answer("Настройка обновлена")


@router.callback_query(AdminCB.filter(F.action == "setting_edit"))
async def cb_setting_edit(
    callback: CallbackQuery,
    callback_data: AdminCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    key = callback_data.code
    if key not in EDITABLE_KEYS:
        await callback.answer("Эту настройку нельзя изменить вручную.", show_alert=True)
        return
    await state.set_state(SettingsForm.waiting_for_value)
    await state.update_data(setting_key=key)
    if key == "reward_amount":
        hint = "Введи новое значение награды в Stars (целое число)."
    else:
        hint = (
            "Введи Gift ID из getAvailableGifts "
            "или отправь «-», чтобы очистить значение."
        )
    await safe_edit(callback, f"✏️ {hint}", admin_cancel_keyboard())
    await callback.answer()


@router.message(SettingsForm.waiting_for_value, F.text)
async def process_setting_value(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    key = data.get("setting_key")
    raw = (message.text or "").strip()

    if key == "reward_amount":
        if not raw.isdigit() or not (1 <= int(raw) <= 100000):
            await message.answer(
                "Некорректное значение. Введи целое число от 1 до 100000."
            )
            return
        value = str(int(raw))
    elif key == "reward_gift_id":
        value = "" if raw in {"-", "—"} else raw[:64]
    else:
        await state.clear()
        await message.answer("Неизвестная настройка.", reply_markup=admin_back_keyboard())
        return

    await settings_service.set_value(session, key, value)
    admin_user = await users_service.get_current_user(session, message.from_user)
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="settings_change",
        details=f"{key} = {value}",
    )
    await session.commit()
    await state.clear()

    values = await settings_service.get_all(session)
    await message.answer(
        "✅ Настройка сохранена.",
        reply_markup=admin_settings_keyboard(values),
    )


@router.message(SettingsForm.waiting_for_value)
async def process_setting_value_non_text(message: Message) -> None:
    await message.answer("Отправь значение текстом.")
