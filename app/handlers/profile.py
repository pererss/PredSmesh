from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import IdeaStatus, User
from app.keyboards import MenuCB, MyIdeaActionCB, MyIdeaCB, MyIdeasCB
from app.keyboards.ideas import (
    my_idea_card_keyboard,
    my_idea_delete_confirm_keyboard,
    my_idea_edit_keyboard,
    my_ideas_keyboard,
)
from app.repositories import ideas as ideas_repo
from app.services import ideas as ideas_service
from app.services import users as users_service
from app.states.ideas import EditIdeaForm
from app.utils.pagination import clamp_page, total_pages
from app.utils.telegram import safe_edit
from app.utils.text import my_idea_card_text

router = Router(name="profile")

PER_PAGE = 5


async def build_my_ideas_view(
    session: AsyncSession, user: User, page: int
) -> tuple[str, InlineKeyboardMarkup]:
    counts = await ideas_repo.count_by_status_for_user(session, user.id)
    total = sum(counts.values())
    pages = total_pages(total, PER_PAGE)
    page = clamp_page(page, total, PER_PAGE)
    ideas = await ideas_repo.list_by_user(
        session, user_id=user.id, offset=page * PER_PAGE, limit=PER_PAGE
    )

    lines = [
        "👤 МОИ ПРЕДЛОЖЕНИЯ",
        "",
        f"Всего предложений: {total}",
        f"📥 На рассмотрении: {counts.get(IdeaStatus.PENDING, 0)}",
        f"✅ Одобрено: {counts.get(IdeaStatus.APPROVED, 0)}",
        f"❌ Отклонено: {counts.get(IdeaStatus.REJECTED, 0)}",
        f"⭐ Награждено: {counts.get(IdeaStatus.REWARDED, 0)}",
    ]

    if total == 0:
        lines += ["", "У тебя пока нет предложений."]
    else:
        lines += ["", "Нажми на предложение, чтобы открыть его полностью."]
        if pages > 1:
            lines.append(f"Страница {page + 1} из {pages}")

    markup = my_ideas_keyboard(
        page=page, total_pages_count=pages, ideas=list(ideas)
    )
    return "\n".join(lines), markup


async def build_my_idea_card(
    session: AsyncSession, user: User, idea_id: int, page: int
) -> tuple[str, InlineKeyboardMarkup] | None:
    idea = await ideas_repo.get_by_id(session, idea_id)
    if idea is None or idea.user_id != user.id:
        return None
    return my_idea_card_text(idea), my_idea_card_keyboard(idea, page)


@router.callback_query(MenuCB.filter(F.action == "myideas"))
async def cb_my_ideas(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    user = await users_service.get_current_user(session, callback.from_user)
    text, markup = await build_my_ideas_view(session, user, page=0)
    await safe_edit(callback, text, markup)


@router.callback_query(MyIdeasCB.filter())
async def cb_my_ideas_page(
    callback: CallbackQuery, callback_data: MyIdeasCB, session: AsyncSession
) -> None:
    await callback.answer()
    user = await users_service.get_current_user(session, callback.from_user)
    text, markup = await build_my_ideas_view(session, user, page=callback_data.page)
    await safe_edit(callback, text, markup)


@router.callback_query(MyIdeaCB.filter())
async def cb_open_my_idea(
    callback: CallbackQuery, callback_data: MyIdeaCB, session: AsyncSession
) -> None:
    user = await users_service.get_current_user(session, callback.from_user)
    card = await build_my_idea_card(
        session, user, callback_data.idea_id, callback_data.page
    )
    if card is None:
        await callback.answer("Предложение не найдено.", show_alert=True)
        return
    await callback.answer()
    text, markup = card
    await safe_edit(callback, text, markup)


@router.callback_query(MyIdeaActionCB.filter(F.action == "edit"))
async def cb_edit_my_idea(
    callback: CallbackQuery,
    callback_data: MyIdeaActionCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    user = await users_service.get_current_user(session, callback.from_user)
    card = await build_my_idea_card(
        session, user, callback_data.idea_id, callback_data.page
    )
    if card is None:
        await callback.answer("Предложение не найдено.", show_alert=True)
        return
    idea = await ideas_repo.get_by_id(session, callback_data.idea_id)
    if idea is None or idea.status != IdeaStatus.PENDING:
        await callback.answer(
            "Редактировать можно только предложения на рассмотрении.",
            show_alert=True,
        )
        return
    await state.set_state(EditIdeaForm.waiting_for_text)
    await state.update_data(idea_id=idea.id, page=callback_data.page)
    await safe_edit(
        callback,
        (
            f"✏️ РЕДАКТИРОВАНИЕ ИДЕИ #{idea.public_number}\n\n"
            "Отправь новый текст предложения одним сообщением.\n\n"
            "Можно отредактировать: что это, для кого, какую проблему решает."
        ),
        my_idea_edit_keyboard(idea, callback_data.page),
    )
    await callback.answer()


@router.message(EditIdeaForm.waiting_for_text, F.text)
async def process_edit_idea_text(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    if message.from_user is None:
        return
    data = await state.get_data()
    idea_id = int(data.get("idea_id", 0))
    page = int(data.get("page", 0))
    idea = await ideas_repo.get_by_id(session, idea_id)
    user = await users_service.get_current_user(session, message.from_user)
    if idea is None or idea.user_id != user.id:
        await state.clear()
        await message.answer("Предложение не найдено.")
        return
    try:
        await ideas_service.update_idea_text(
            session, idea=idea, user=user, text_value=message.text or ""
        )
    except ideas_service.IdeaValidationError as exc:
        await message.answer(str(exc))
        return
    except ideas_service.IdeaActionError as exc:
        await state.clear()
        await message.answer(str(exc))
        return
    await state.clear()
    text, markup = my_idea_card_text(idea), my_idea_card_keyboard(idea, page)
    await message.answer(f"✅ Текст обновлён.\n\n{text}", reply_markup=markup)


@router.message(EditIdeaForm.waiting_for_text)
async def process_edit_idea_non_text(message: Message) -> None:
    await message.answer("Отправь новый текст идеи текстовым сообщением.")


@router.callback_query(MyIdeaActionCB.filter(F.action == "delete"))
async def cb_delete_my_idea(
    callback: CallbackQuery,
    callback_data: MyIdeaActionCB,
    session: AsyncSession,
) -> None:
    user = await users_service.get_current_user(session, callback.from_user)
    idea = await ideas_repo.get_by_id(session, callback_data.idea_id)
    if idea is None or idea.user_id != user.id:
        await callback.answer("Предложение не найдено.", show_alert=True)
        return
    if idea.status != IdeaStatus.PENDING:
        await callback.answer(
            "Удалить можно только предложение на рассмотрении.",
            show_alert=True,
        )
        return
    await safe_edit(
        callback,
        (
            f"🗑 Удалить предложение #{idea.public_number}?\n\n"
            "Действие нельзя отменить."
        ),
        my_idea_delete_confirm_keyboard(idea, callback_data.page),
    )
    await callback.answer()


@router.callback_query(MyIdeaActionCB.filter(F.action == "delete_confirm"))
async def cb_delete_my_idea_confirm(
    callback: CallbackQuery,
    callback_data: MyIdeaActionCB,
    session: AsyncSession,
) -> None:
    user = await users_service.get_current_user(session, callback.from_user)
    idea = await ideas_repo.get_by_id(session, callback_data.idea_id)
    if idea is None or idea.user_id != user.id:
        await callback.answer("Предложение не найдено.", show_alert=True)
        return
    number = idea.public_number
    try:
        await ideas_service.withdraw_idea(session, idea=idea, user=user)
    except ideas_service.IdeaActionError as exc:
        await callback.answer(str(exc), show_alert=True)
        return
    await session.commit()
    text, markup = await build_my_ideas_view(session, user, page=callback_data.page)
    await safe_edit(callback, f"🗑 Предложение #{number} удалено.\n\n{text}", markup)
    await callback.answer("Предложение удалено")
