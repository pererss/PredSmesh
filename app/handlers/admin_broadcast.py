from __future__ import annotations

import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import AdminCB
from app.keyboards.admin import (
    admin_back_keyboard,
    admin_cancel_keyboard,
    broadcast_preview_keyboard,
)
from app.repositories import users as users_repo
from app.services import admin as admin_log
from app.services import users as users_service
from app.states.admin import BroadcastForm
from app.utils.telegram import IsAdmin, safe_edit
from app.utils.text import escape_html, truncate

logger = logging.getLogger(__name__)

router = Router(name="admin_broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

CHUNK_SIZE = 100
BROADCAST_DELAY = 0.05


async def _send_broadcast_message(
    bot, telegram_id: int, text_value: str
) -> tuple[bool, str]:
    try:
        await bot.send_message(telegram_id, text_value, parse_mode=None)
        return True, "ok"
    except TelegramForbiddenError:
        logger.info("User %s blocked the bot during broadcast", telegram_id)
        return False, "blocked"
    except TelegramRetryAfter as exc:
        await asyncio.sleep(exc.retry_after + 1)
        try:
            await bot.send_message(telegram_id, text_value, parse_mode=None)
            return True, "ok"
        except TelegramForbiddenError:
            return False, "blocked"
        except TelegramAPIError as retry_exc:
            logger.warning(
                "Broadcast to %s failed after retry: %s", telegram_id, retry_exc
            )
            return False, "failed"
    except TelegramAPIError as exc:
        logger.warning("Broadcast to %s failed: %s", telegram_id, exc)
        return False, "failed"


async def _run_broadcast(
    bot, session: AsyncSession, text_value: str
) -> tuple[int, int, int]:
    sent = 0
    blocked = 0
    failed = 0
    offset = 0
    while True:
        users = await users_repo.list_active_paginated(
            session, offset=offset, limit=CHUNK_SIZE
        )
        if not users:
            break
        for user in users:
            ok, reason = await _send_broadcast_message(
                bot, user.telegram_id, text_value
            )
            if ok:
                sent += 1
            elif reason == "blocked":
                blocked += 1
                user.is_active = False
            else:
                failed += 1
            await asyncio.sleep(BROADCAST_DELAY)
        offset += CHUNK_SIZE
        await session.commit()
    return sent, blocked, failed


@router.callback_query(AdminCB.filter(F.action == "broadcast"))
async def cb_broadcast_prompt(
    callback: CallbackQuery, state: FSMContext
) -> None:
    await state.set_state(BroadcastForm.waiting_for_text)
    await safe_edit(
        callback,
        (
            "📢 РАССЫЛКА\n\n"
            "Отправь текст рассылки одним сообщением.\n"
            "Сообщение уйдёт всем активным пользователям."
        ),
        admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(BroadcastForm.waiting_for_text, F.text)
async def process_broadcast_text(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    text_value = (message.text or "").strip()
    if not text_value:
        await message.answer("Текст пустой. Отправь текст рассылки.")
        return
    total = await users_repo.count_active(session)
    await state.set_state(BroadcastForm.confirm)
    await state.update_data(broadcast_text=text_value)
    await message.answer(
        (
            "📢 ПРЕДПРОСМОТР РАССЫЛКИ\n\n"
            f"Получателей: {total}\n\n"
            f"{escape_html(truncate(text_value, 3000))}"
        ),
        reply_markup=broadcast_preview_keyboard(),
    )


@router.message(BroadcastForm.waiting_for_text)
async def process_broadcast_non_text(message: Message) -> None:
    await message.answer("Отправь текст рассылки текстовым сообщением.")


@router.message(StateFilter(BroadcastForm.confirm))
async def process_broadcast_confirm_text(message: Message) -> None:
    await message.answer(
        "Нажми «📤 Отправить» или «❌ Отмена» под предпросмотром рассылки."
    )


@router.callback_query(
    AdminCB.filter(F.action == "broadcast_send"), StateFilter(BroadcastForm.confirm)
)
async def cb_broadcast_send(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    text_value = data.get("broadcast_text", "")
    if not text_value:
        await state.clear()
        await callback.answer("Текст рассылки потерян, начни заново.", show_alert=True)
        return

    await callback.answer("Рассылка началась")
    admin_user = await users_service.get_current_user(session, callback.from_user)
    sent, blocked, failed = await _run_broadcast(callback.bot, session, text_value)

    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="broadcast",
        details=(
            f"Рассылка: отправлено {sent}, заблокировали бота {blocked}, ошибок {failed}"
        ),
    )
    await session.commit()
    await state.clear()
    await safe_edit(
        callback,
        (
            "📢 РАССЫЛКА ЗАВЕРШЕНА\n\n"
            f"✅ Отправлено: {sent}\n"
            f"🚫 Заблокировали бота: {blocked}\n"
            f"⚠️ Ошибок: {failed}"
        ),
        admin_back_keyboard(),
    )


@router.callback_query(AdminCB.filter(F.action == "broadcast_cancel"))
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(callback, "Рассылка отменена.", admin_back_keyboard())
    await callback.answer()
