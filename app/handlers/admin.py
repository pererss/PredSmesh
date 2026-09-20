from __future__ import annotations

import csv
import io
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import IdeaStatus
from app.handlers.admin_ideas import send_admin_idea_card
from app.handlers.admin_users import build_user_card
from app.keyboards import AdminCB
from app.keyboards.admin import admin_back_keyboard, admin_menu_keyboard
from app.repositories import ideas as ideas_repo
from app.repositories import users as users_repo
from app.services import admin as admin_log
from app.services import statistics as statistics_service
from app.services import users as users_service
from app.states.admin import AdminSearchForm
from app.utils.telegram import IsAdmin, safe_edit

logger = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def render_panel(session: AsyncSession) -> tuple[str, object]:
    pending = await ideas_repo.count_by_status(session, IdeaStatus.PENDING)
    text = (
        "🛠 АДМИН-ПАНЕЛЬ\n\n"
        f"📥 Новых предложений: {pending}\n\n"
        "Выбери раздел:"
    )
    return text, admin_menu_keyboard(pending)


@router.message(Command("admin"))
async def cmd_admin(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    text, markup = await render_panel(session)
    await message.answer(text, reply_markup=markup)


@router.callback_query(AdminCB.filter(F.action == "panel"))
async def cb_panel(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await state.clear()
    text, markup = await render_panel(session)
    await safe_edit(callback, text, markup)
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


@router.callback_query(AdminCB.filter(F.action == "search"))
async def cb_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminSearchForm.waiting_for_query)
    await safe_edit(
        callback,
        (
            "🔍 ПОИСК\n\n"
            "Отправь одним сообщением:\n"
            "• номер идеи (например, 12)\n"
            "• Telegram ID пользователя (например, 5434264152)\n"
            "• @username пользователя"
        ),
        admin_back_keyboard(),
    )
    await callback.answer()


@router.message(AdminSearchForm.waiting_for_query, F.text)
async def process_search(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    query = (message.text or "").strip()
    await state.clear()
    if not query:
        await message.answer("Пустой запрос.", reply_markup=admin_back_keyboard())
        return

    if query.startswith("@"):
        user = await users_repo.get_by_username(session, query)
        if user is None:
            await message.answer(
                f"Пользователь {query} не найден.",
                reply_markup=admin_back_keyboard(),
            )
            return
        text, markup = await build_user_card(session, user, page=0)
        await message.answer(text, reply_markup=markup)
        return

    if query.isdigit():
        if len(query) <= 6:
            idea = await ideas_repo.get_by_public_number(session, int(query))
            if idea is not None:
                await send_admin_idea_card(message, session, idea)
                return
        user = await users_repo.get_by_telegram_id(session, int(query))
        if user is not None:
            text, markup = await build_user_card(session, user, page=0)
            await message.answer(text, reply_markup=markup)
            return
        await message.answer(
            "Ни идея с таким номером, ни пользователь с таким ID не найдены.",
            reply_markup=admin_back_keyboard(),
        )
        return

    await message.answer(
        "Не понял запрос. Отправь номер идеи, Telegram ID или @username.",
        reply_markup=admin_back_keyboard(),
    )


@router.message(AdminSearchForm.waiting_for_query)
async def process_search_non_text(message: Message) -> None:
    await message.answer("Отправь запрос текстом.")


@router.callback_query(AdminCB.filter(F.action == "export"))
async def cb_export(callback: CallbackQuery, session: AsyncSession) -> None:
    ideas = await ideas_repo.list_all_with_authors(session)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [
            "number",
            "status",
            "author_telegram_id",
            "author_username",
            "text",
            "created_at",
            "approved_at",
            "rewarded_at",
            "rejection_reason",
        ]
    )
    for idea in ideas:
        author = idea.author
        writer.writerow(
            [
                idea.public_number,
                idea.status.value,
                author.telegram_id if author else "",
                author.username if author and author.username else "",
                idea.text.replace("\r\n", " ").replace("\n", " "),
                idea.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                idea.approved_at.strftime("%Y-%m-%d %H:%M:%S")
                if idea.approved_at
                else "",
                idea.rewarded_at.strftime("%Y-%m-%d %H:%M:%S")
                if idea.rewarded_at
                else "",
                (idea.rejection_reason or "").replace("\n", " "),
            ]
        )

    data = buffer.getvalue().encode("utf-8-sig")
    admin_user = await users_service.get_current_user(session, callback.from_user)
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="export",
        details=f"Экспорт идей: {len(ideas)} записей",
    )
    await session.commit()

    if callback.message is not None and isinstance(callback.message, Message):
        await callback.message.answer_document(
            BufferedInputFile(data, filename="ideas_export.csv"),
            caption=f"📤 Экспорт идей: {len(ideas)} записей",
        )
    await callback.answer("Экспорт готов")
