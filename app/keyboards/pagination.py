from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton


def pagination_buttons(
    *,
    page: int,
    total_pages_count: int,
    prev_callback: CallbackData,
    next_callback: CallbackData,
) -> list[InlineKeyboardButton]:
    buttons: list[InlineKeyboardButton] = []
    if total_pages_count > 1 and page > 0:
        buttons.append(
            InlineKeyboardButton(text="◀️", callback_data=prev_callback.pack())
        )
    if total_pages_count > 1 and page < total_pages_count - 1:
        buttons.append(
            InlineKeyboardButton(text="▶️", callback_data=next_callback.pack())
        )
    return buttons
