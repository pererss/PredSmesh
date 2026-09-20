from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import IdeaStatus, User
from app.keyboards import MenuCB, MyIdeasCB
from app.keyboards.ideas import my_ideas_keyboard
from app.repositories import ideas as ideas_repo
from app.services import users as users_service
from app.utils.pagination import clamp_page, total_pages
from app.utils.telegram import safe_edit
from app.utils.text import STATUS_LABELS, escape_html, format_date, truncate

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
        for idea in ideas:
            lines += [
                "",
                (
                    f"#{idea.public_number} • "
                    f"{STATUS_LABELS.get(idea.status, idea.status)} • "
                    f"{format_date(idea.created_at)}"
                ),
                f"«{escape_html(truncate(idea.text, 120))}»",
            ]
        if pages > 1:
            lines += ["", f"Страница {page + 1} из {pages}"]

    markup = my_ideas_keyboard(
        page=page, total_pages_count=pages, has_ideas=total > 0
    )
    return "\n".join(lines), markup


@router.callback_query(MenuCB.filter(F.action == "myideas"))
async def cb_my_ideas(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    user = await users_service.get_current_user(session, callback.from_user)
    text, markup = await build_my_ideas_view(session, user, page=0)
    await safe_edit(callback, text, markup)
    await callback.answer()


@router.callback_query(MyIdeasCB.filter())
async def cb_my_ideas_page(
    callback: CallbackQuery, callback_data: MyIdeasCB, session: AsyncSession
) -> None:
    user = await users_service.get_current_user(session, callback.from_user)
    text, markup = await build_my_ideas_view(session, user, page=callback_data.page)
    await safe_edit(callback, text, markup)
    await callback.answer()
