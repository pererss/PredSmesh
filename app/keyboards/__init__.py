from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton


class MenuCB(CallbackData, prefix="menu"):
    action: str


class CatalogCB(CallbackData, prefix="cat"):
    mode: str
    page: int = 0


class LikeCB(CallbackData, prefix="like"):
    idea_id: int
    mode: str = "new"
    page: int = 0


class MyIdeasCB(CallbackData, prefix="my"):
    page: int = 0


class MyIdeaCB(CallbackData, prefix="mi"):
    idea_id: int
    page: int = 0


class MyIdeaActionCB(CallbackData, prefix="mia"):
    action: str
    idea_id: int
    page: int = 0


class AdminCB(CallbackData, prefix="adm"):
    action: str
    entity_id: int = 0
    page: int = 0
    code: str = ""


class RejectApplyCB(CallbackData, prefix="rej"):
    idea_id: int
    reason: str
    queue: int = 0
    page: int = 0


class CategoryToggleCB(CallbackData, prefix="catt"):
    idea_id: int
    category_id: int
    queue: int = 0
    page: int = 0


def cb_button(text: str, callback_data: CallbackData) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data.pack())


def url_button(text: str, url: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, url=url)
