from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ErrorEvent, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.start import render_main_menu_text
from app.keyboards import MenuCB
from app.keyboards.user import main_menu_keyboard
from app.utils.telegram import safe_edit

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
