from __future__ import annotations

from urllib.parse import quote

from aiogram.types import InlineKeyboardMarkup

from app.database.models import Idea, IdeaStatus
from app.keyboards import (
    AdminCB,
    CatalogCB,
    LikeCB,
    MenuCB,
    MyIdeaActionCB,
    MyIdeaCB,
    MyIdeasCB,
    cb_button,
    url_button,
)
from app.keyboards.pagination import pagination_buttons
from app.utils.text import STATUS_LABELS


def catalog_modes_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            cb_button("🆕 Новые", CatalogCB(mode="new")),
            cb_button("🔥 Популярные", CatalogCB(mode="pop")),
        ],
        [cb_button("🎲 Случайная", CatalogCB(mode="rand"))],
        [cb_button("🛠 Админ-панель", AdminCB(action="panel"))],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def catalog_nav_keyboard(
    *,
    mode: str,
    page: int,
    total_pages_count: int,
    idea_id: int,
    liked: bool,
) -> InlineKeyboardMarkup:
    rows = [
        [
            cb_button(
                "💔 Убрать лайк" if liked else "❤️ Поставить лайк",
                LikeCB(idea_id=idea_id, mode=mode, page=page),
            )
        ]
    ]
    nav = pagination_buttons(
        page=page,
        total_pages_count=total_pages_count,
        prev_callback=CatalogCB(mode=mode, page=page - 1),
        next_callback=CatalogCB(mode=mode, page=page + 1),
    )
    if nav:
        rows.append(nav)
    rows.append(
        [
            cb_button("🔙 К разделам", MenuCB(action="catalog")),
            cb_button("🛠 Админ-панель", AdminCB(action="panel")),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def random_idea_keyboard(*, idea_id: int, liked: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            cb_button(
                "💔 Убрать лайк" if liked else "❤️ Поставить лайк",
                LikeCB(idea_id=idea_id, mode="rand", page=0),
            )
        ],
        [cb_button("🎲 Другая идея", CatalogCB(mode="rand"))],
        [
            cb_button("🔙 К разделам", MenuCB(action="catalog")),
            cb_button("🛠 Админ-панель", AdminCB(action="panel")),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def catalog_empty_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            cb_button("🔙 К разделам", MenuCB(action="catalog")),
            cb_button("🛠 Админ-панель", AdminCB(action="panel")),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_ideas_keyboard(
    *, page: int, total_pages_count: int, ideas: list[Idea]
) -> InlineKeyboardMarkup:
    rows: list[list] = []
    for idea in ideas:
        rows.append(
            [
                cb_button(
                    (
                        f"#{idea.public_number} • "
                        f"{STATUS_LABELS.get(idea.status, idea.status)}"
                    ),
                    MyIdeaCB(idea_id=idea.id, page=page),
                )
            ]
        )
    nav = pagination_buttons(
        page=page,
        total_pages_count=total_pages_count,
        prev_callback=MyIdeasCB(page=page - 1),
        next_callback=MyIdeasCB(page=page + 1),
    )
    if nav:
        rows.append(nav)
    if not ideas:
        rows.append([cb_button("💡 Предложить идею", MenuCB(action="submit"))])
    rows.append([cb_button("🏠 В меню", MenuCB(action="menu"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_idea_card_keyboard(idea: Idea, page: int) -> InlineKeyboardMarkup:
    rows: list[list] = []
    if idea.status == IdeaStatus.PENDING:
        rows.append(
            [
                cb_button(
                    "✏️ Редактировать",
                    MyIdeaActionCB(action="edit", idea_id=idea.id, page=page),
                ),
                cb_button(
                    "🗑 Удалить",
                    MyIdeaActionCB(action="delete", idea_id=idea.id, page=page),
                ),
            ]
        )
    rows.append([cb_button("🔙 К моим предложениям", MyIdeasCB(page=page))])
    rows.append([cb_button("🏠 В меню", MenuCB(action="menu"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_idea_delete_confirm_keyboard(idea: Idea, page: int) -> InlineKeyboardMarkup:
    rows = [
        [
            cb_button(
                "✅ Да, удалить",
                MyIdeaActionCB(action="delete_confirm", idea_id=idea.id, page=page),
            )
        ],
        [cb_button("❌ Отмена", MyIdeaCB(idea_id=idea.id, page=page))],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_idea_edit_keyboard(idea: Idea, page: int) -> InlineKeyboardMarkup:
    rows = [[cb_button("❌ Отмена", MyIdeaCB(idea_id=idea.id, page=page))]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def referrals_keyboard(link: str) -> InlineKeyboardMarkup:
    share_text = "Присоединяйся к проекту идей!"
    share_url = (
        f"https://t.me/share/url?url={quote(link, safe='')}"
        f"&text={quote(share_text, safe='')}"
    )
    rows = [
        [url_button("📤 Поделиться", share_url)],
        [cb_button("🏠 В меню", MenuCB(action="menu"))],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
