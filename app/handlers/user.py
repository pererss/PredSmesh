from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ErrorEvent, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.start import render_main_menu_text
from app.keyboards import MenuCB
from app.keyboards.admin import admin_contact_keyboard
from app.keyboards.user import cancel_keyboard, main_menu_keyboard
from app.services import users as users_service
from app.services.notifications import notify_admin
from app.states.ideas import ContactForm
from app.utils.telegram import safe_edit
from app.utils.text import CONTACT_PROMPT, author_display, escape_html, truncate

logger = logging.getLogger(__name__)

router = Router(name="user")


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await message.answer(
        await render_main_menu_text(session), reply_markup=main_menu_keyboard()
    )


@router.callback_query(MenuCB.filter(F.action == "cancel"))
async def cb_cancel(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await safe_edit(
        callback, await render_main_menu_text(session), main_menu_keyboard()
    )
    await callback.answer("Действие отменено")


@router.callback_query(MenuCB.filter(F.action == "contact"))
async def cb_contact(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await state.set_state(ContactForm.waiting_for_text)
    await safe_edit(callback, CONTACT_PROMPT, cancel_keyboard())
    await callback.answer()


@router.message(ContactForm.waiting_for_text, F.text)
async def process_contact_text(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    if message.from_user is None:
        return
    text_value = (message.text or "").strip()
    if len(text_value) < 5:
        await message.answer("Сообщение слишком короткое. Опиши вопрос подробнее.")
        return

    user = await users_service.get_current_user(session, message.from_user)
    await state.clear()
    await message.answer(
        "✅ Сообщение отправлено администрации. Ответ придёт сюда."
    )
    await notify_admin(
        message.bot,
        (
            "📩 СООБЩЕНИЕ ОТ ПОЛЬЗОВАТЕЛЯ\n\n"
            f"👤 {author_display(user)}\n"
            f"🆔 {user.telegram_id}\n\n"
            f"{escape_html(truncate(text_value, 3500))}"
        ),
        admin_contact_keyboard(user.id),
    )


@router.message(ContactForm.waiting_for_text)
async def process_contact_non_text(message: Message) -> None:
    await message.answer("Отправь сообщение текстом.")


@router.message(Command("admin"))
async def cmd_admin_denied(message: Message) -> None:
    await message.answer("⛔ У тебя нет доступа к админ-панели.")


@router.message()
async def fallback_message(message: Message) -> None:
    await message.answer(
        "🤔 Я тебя не понял. Выбери действие в меню ниже 👇",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query()
async def fallback_callback(callback: CallbackQuery) -> None:
    await callback.answer("Это действие недоступно.", show_alert=False)


async def on_error(event: ErrorEvent) -> bool:
    logger.error(
        "Unhandled error while processing update", exc_info=event.exception
    )
    update = event.update
    try:
        if update.callback_query is not None:
            await update.callback_query.answer(
                "Произошла ошибка. Попробуй ещё раз.", show_alert=True
            )
        elif update.message is not None:
            await update.message.answer(
                "Произошла непредвиденная ошибка. Попробуй ещё раз позже."
            )
    except Exception:
        logger.debug("Failed to notify user about error", exc_info=True)
    return True
