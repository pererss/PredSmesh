from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup

from app.keyboards import MenuCB, cb_button


def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [cb_button("💡 Предложить идею", MenuCB(action="submit"))],
        [
            cb_button("🔎 Посмотреть идеи", MenuCB(action="catalog")),
            cb_button("🏆 Лучшие идеи", MenuCB(action="best")),
        ],
        [
            cb_button("❓ Как это работает", MenuCB(action="how")),
            cb_button("👤 Мои предложения", MenuCB(action="myideas")),
        ],
        [cb_button("🎁 Пригласить друзей", MenuCB(action="referrals"))],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def how_it_works_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [cb_button("💡 Предложить идею", MenuCB(action="submit"))],
        [cb_button("🏠 В меню", MenuCB(action="menu"))],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [[cb_button("🏠 В меню", MenuCB(action="menu"))]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_keyboard() -> InlineKeyboardMarkup:
    rows = [[cb_button("❌ Отмена", MenuCB(action="cancel"))]]
    return InlineKeyboardMarkup(inline_keyboard=rows)
