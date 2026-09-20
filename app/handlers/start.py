from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.profile import build_my_ideas_view
from app.keyboards import MenuCB
from app.keyboards.user import how_it_works_keyboard, main_menu_keyboard
from app.services import referrals as referrals_service
from app.services import settings as settings_service
from app.services import users as users_service
from app.services.notifications import notify_user
from app.utils.telegram import safe_edit
from app.utils.text import HOW_IT_WORKS_TEXT, MAIN_MENU_TEXT

logger = logging.getLogger(__name__)

router = Router(name="start")


async def render_main_menu_text(session: AsyncSession) -> str:
    reward_amount = await settings_service.get_int(session, "reward_amount", 15)
    return MAIN_MENU_TEXT.format(reward=reward_amount)


async def render_how_it_works_text(session: AsyncSession) -> str:
    reward_amount = await settings_service.get_int(session, "reward_amount", 15)
    return HOW_IT_WORKS_TEXT.format(reward=reward_amount)


async def _handle_referral_payload(
    message: Message, session: AsyncSession, user, payload: str | None
) -> None:
    if not payload or not payload.startswith("ref_"):
        return
    raw_id = payload[4:]
    if not raw_id.isdigit():
        return
    referrer = await referrals_service.register_referral(
        session, referred_user=user, referrer_telegram_id=int(raw_id)
    )
    if referrer is None:
        return
    count = await referrals_service.count_referrals(session, referrer.id)
    await notify_user(
        message.bot,
        session,
        referrer.telegram_id,
        (
            "🎉 По твоей ссылке присоединился новый пользователь!\n\n"
            f"👥 Ты пригласил: {count} пользователей."
        ),
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    if message.from_user is None:
        return
    user = await users_service.get_current_user(session, message.from_user)
    await _handle_referral_payload(message, session, user, command.args)
    await message.answer(
        await render_main_menu_text(session), reply_markup=main_menu_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession) -> None:
    await message.answer(
        await render_how_it_works_text(session),
        reply_markup=how_it_works_keyboard(),
    )


@router.message(Command("menu"))
async def cmd_menu(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await message.answer(
        await render_main_menu_text(session), reply_markup=main_menu_keyboard()
    )


@router.message(Command("myideas"))
async def cmd_my_ideas(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await users_service.get_current_user(session, message.from_user)
    text, markup = await build_my_ideas_view(session, user, page=0)
    await message.answer(text, reply_markup=markup)


@router.callback_query(MenuCB.filter(F.action == "menu"))
async def cb_main_menu(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    await safe_edit(callback, await render_main_menu_text(session), main_menu_keyboard())
    await callback.answer()


@router.callback_query(MenuCB.filter(F.action == "how"))
async def cb_how_it_works(callback: CallbackQuery, session: AsyncSession) -> None:
    await safe_edit(
        callback, await render_how_it_works_text(session), how_it_works_keyboard()
    )
    await callback.answer()
