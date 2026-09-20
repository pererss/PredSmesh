from __future__ import annotations

from urllib.parse import quote

from aiogram.types import InlineKeyboardMarkup

from app.keyboards import CatalogCB, LikeCB, MenuCB, MyIdeasCB, cb_button, url_button
from app.keyboards.pagination import pagination_buttons


def catalog_modes_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            cb_button("🆕 Новые", CatalogCB(mode="new")),
            cb_button("🔥 Популярные", CatalogCB(mode="pop")),
        ],
        [cb_button("🎲 Случайная", CatalogCB(mode="rand"))],
        [cb_button("🏠 В меню", MenuCB(action="menu"))],
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
            cb_button("🏠 В меню", MenuCB(action="menu")),
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
            cb_button("🏠 В меню", MenuCB(action="menu")),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def catalog_empty_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            cb_button("🔙 К разделам", MenuCB(action="catalog")),
            cb_button("🏠 В меню", MenuCB(action="menu")),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_ideas_keyboard(
    *, page: int, total_pages_count: int, has_ideas: bool
) -> InlineKeyboardMarkup:
    rows: list[list] = []
    if has_ideas:
        nav = pagination_buttons(
            page=page,
            total_pages_count=total_pages_count,
            prev_callback=MyIdeasCB(page=page - 1),
            next_callback=MyIdeasCB(page=page + 1),
        )
        if nav:
            rows.append(nav)
    else:
        rows.append([cb_button("💡 Предложить идею", MenuCB(action="submit"))])
    rows.append([cb_button("🏠 В меню", MenuCB(action="menu"))])
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
