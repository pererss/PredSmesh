from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import MenuCB
from app.keyboards.user import cancel_keyboard
from app.services import ideas as ideas_service
from app.services import settings as settings_service
from app.services.notifications import notify_idea_submitted
from app.states.ideas import IdeaForm
from app.utils.telegram import safe_edit
from app.utils.text import IDEA_CONFIRMATION_TEXT, IDEA_SUBMISSION_PROMPT

logger = logging.getLogger(__name__)

router = Router(name="ideas")


@router.callback_query(MenuCB.filter(F.action == "submit"))
async def cb_submit(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    enabled = await settings_service.get_bool(session, "submissions_enabled", True)
    if not enabled:
        await callback.answer(
            "Приём идей временно приостановлен.", show_alert=True
        )
        return
    await state.set_state(IdeaForm.waiting_for_text)
    await safe_edit(callback, IDEA_SUBMISSION_PROMPT, cancel_keyboard())
    await callback.answer()


@router.message(IdeaForm.waiting_for_text, F.text)
async def process_idea_text(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    if message.from_user is None or message.text is None:
        return
    try:
        idea, author = await ideas_service.submit_idea(
            session, telegram_user=message.from_user, text_value=message.text
        )
    except ideas_service.IdeaValidationError as exc:
        await message.answer(str(exc))
        return
    except ideas_service.SubmissionsDisabledError as exc:
        await state.clear()
        await message.answer(str(exc))
        return

    await session.commit()
    await state.clear()

    reward_amount = await settings_service.get_int(session, "reward_amount", 15)
    await message.answer(
        IDEA_CONFIRMATION_TEXT.format(
            reward=reward_amount, number=idea.public_number
        )
    )
    await notify_idea_submitted(message.bot, idea, author, reward_amount)


@router.message(IdeaForm.waiting_for_text)
async def process_idea_non_text(message: Message) -> None:
    await message.answer("Пожалуйста, отправь идею текстовым сообщением.")
