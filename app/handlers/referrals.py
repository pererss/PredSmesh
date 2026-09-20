from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import MenuCB
from app.keyboards.ideas import referrals_keyboard
from app.services import referrals as referrals_service
from app.services import users as users_service
from app.utils.telegram import resolve_bot_username, safe_edit

router = Router(name="referrals")


@router.callback_query(MenuCB.filter(F.action == "referrals"))
async def cb_referrals(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await users_service.get_current_user(session, callback.from_user)
    bot_username = await resolve_bot_username(callback.bot)
    link = referrals_service.build_referral_link(bot_username, callback.from_user.id)
    count = await referrals_service.count_referrals(session, user.id)
    text = (
        "🎁 ПРИГЛАСИ ДРУЗЕЙ\n\n"
        "Отправь другу свою ссылку — по ней он попадёт в бота:\n\n"
        f"<code>{link}</code>\n\n"
        f"👥 Ты пригласил: {count} пользователей."
    )
    await safe_edit(callback, text, referrals_keyboard(link))
    await callback.answer()
