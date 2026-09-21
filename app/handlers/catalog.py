from __future__ import annotations

import logging
from math import ceil

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Idea, IdeaStatus
from app.keyboards import CatalogCB, LikeCB, MenuCB
from app.keyboards.ideas import (
    catalog_empty_keyboard,
    catalog_modes_keyboard,
    catalog_nav_keyboard,
    random_idea_keyboard,
)
from app.repositories import ideas as ideas_repo
from app.repositories import likes as likes_repo
from app.services import ideas as ideas_service
from app.services import users as users_service
from app.utils.telegram import IsAdmin, safe_edit
from app.utils.text import catalog_idea_card_text

logger = logging.getLogger(__name__)

router = Router(name="catalog")
router.callback_query.filter(IsAdmin())

PER_PAGE = 1
HEADERS = {
    "new": "🆕 Новые идеи",
    "pop": "🔥 Популярные идеи",
    "rand": "🎲 Случайная идея",
}
ORDER_BY_LIKES = {"pop"}


async def _mark_viewed_if_new(state: FSMContext, idea_id: int) -> bool:
    data = await state.get_data()
    viewed = set(data.get("viewed_ideas", []))
    if idea_id in viewed:
        return False
    viewed.add(idea_id)
    if len(viewed) > 300:
        viewed = set(sorted(viewed)[-200:])
    await state.update_data(viewed_ideas=sorted(viewed))
    return True


async def _fetch_page(session: AsyncSession, *, mode: str, page: int) -> Idea | None:
    ideas = await ideas_repo.list_approved_paginated(
        session,
        offset=page * PER_PAGE,
        limit=PER_PAGE,
        order_by_likes=mode in ORDER_BY_LIKES,
    )
    return ideas[0] if ideas else None


async def _render_idea_card(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    idea: Idea,
    mode: str,
    page: int,
    *,
    increment_views: bool,
) -> None:
    if increment_views and await _mark_viewed_if_new(state, idea.id):
        await ideas_service.register_view(session, idea=idea)

    user = await users_service.get_current_user(session, callback.from_user)
    liked = await likes_repo.is_liked(session, idea_id=idea.id, user_id=user.id)

    text = catalog_idea_card_text(idea, header=HEADERS[mode], author=idea.author)
    if mode == "rand":
        markup = random_idea_keyboard(idea_id=idea.id, liked=liked)
    else:
        total = await ideas_repo.count_approved(session)
        total_pages_count = max(1, ceil(total / PER_PAGE))
        page = min(max(page, 0), total_pages_count - 1)
        markup = catalog_nav_keyboard(
            mode=mode,
            page=page,
            total_pages_count=total_pages_count,
            idea_id=idea.id,
            liked=liked,
        )
    await safe_edit(callback, text, markup)


@router.callback_query(MenuCB.filter(F.action == "catalog"))
async def cb_catalog(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    await callback.answer()
    total = await ideas_repo.count_approved(session)
    text = (
        "🔎 ИДЕИ ПРОЕКТОВ\n\n"
        f"Опубликованных идей: {total}.\n\n"
        "Выбери раздел:"
    )
    await safe_edit(callback, text, catalog_modes_keyboard())


@router.callback_query(CatalogCB.filter(F.mode.in_({"new", "pop"})))
async def cb_catalog_page(
    callback: CallbackQuery,
    callback_data: CatalogCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await callback.answer()
    total = await ideas_repo.count_approved(session)
    total_pages_count = max(1, ceil(total / PER_PAGE))
    page = min(max(callback_data.page, 0), total_pages_count - 1)
    idea = await _fetch_page(session, mode=callback_data.mode, page=page)
    if idea is None:
        await safe_edit(
            callback, "Пока здесь нет опубликованных идей.", catalog_empty_keyboard()
        )
    else:
        await _render_idea_card(
            callback,
            session,
            state,
            idea,
            callback_data.mode,
            page,
            increment_views=True,
        )


@router.callback_query(CatalogCB.filter(F.mode == "rand"))
async def cb_random(
    callback: CallbackQuery, session: AsyncSession, state: FSMContext
) -> None:
    await callback.answer()
    idea = await ideas_repo.get_random_approved(session)
    if idea is None:
        await safe_edit(
            callback, "Пока здесь нет опубликованных идей.", catalog_empty_keyboard()
        )
    else:
        await _render_idea_card(
            callback, session, state, idea, "rand", 0, increment_views=True
        )


@router.callback_query(LikeCB.filter())
async def cb_like(
    callback: CallbackQuery,
    callback_data: LikeCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.idea_id)
    if idea is None or idea.status != IdeaStatus.APPROVED:
        await callback.answer("Эта идея больше недоступна.", show_alert=True)
        return
    user = await users_service.get_current_user(session, callback.from_user)
    liked, _likes_count = await ideas_service.toggle_like(
        session, idea=idea, user=user
    )
    await _render_idea_card(
        callback,
        session,
        state,
        idea,
        callback_data.mode,
        callback_data.page,
        increment_views=False,
    )
    await callback.answer("❤️ Лайк добавлен" if liked else "💔 Лайк убран")
