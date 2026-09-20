from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramForbiddenError,
    TelegramRetryAfter,
)
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.models import Idea, User
from app.keyboards.admin import admin_idea_actions_keyboard
from app.repositories import users as users_repo
from app.services import settings as settings_service
from app.utils.text import admin_idea_card_text

logger = logging.getLogger(__name__)


async def notify_admin(
    bot: Bot, text: str, reply_markup: InlineKeyboardMarkup | None = None
) -> bool:
    try:
        await bot.send_message(
            get_settings().admin_id, text, reply_markup=reply_markup
        )
        return True
    except TelegramAPIError as exc:
        logger.warning("Failed to notify admin: %s", exc)
        return False


async def notify_user(
    bot: Bot,
    session: AsyncSession,
    telegram_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    force: bool = False,
) -> bool:
    if not force:
        enabled = await settings_service.get_bool(
            session, "notifications_enabled", True
        )
        if not enabled:
            logger.info(
                "Notifications are disabled in settings; skipping user %s",
                telegram_id,
            )
            return False

    try:
        await bot.send_message(telegram_id, text, reply_markup=reply_markup)
        return True
    except TelegramForbiddenError:
        logger.info("User %s blocked the bot; deactivating", telegram_id)
        await users_repo.set_active_by_telegram_id(session, telegram_id, False)
        return False
    except TelegramRetryAfter as exc:
        await asyncio.sleep(exc.retry_after + 1)
        try:
            await bot.send_message(telegram_id, text, reply_markup=reply_markup)
            return True
        except TelegramAPIError as retry_exc:
            logger.warning(
                "Failed to notify user %s after retry: %s", telegram_id, retry_exc
            )
            return False
    except TelegramAPIError as exc:
        logger.warning("Failed to notify user %s: %s", telegram_id, exc)
        return False


async def notify_idea_submitted(
    bot: Bot,
    idea: Idea,
    author: User,
    reward_amount: int,
) -> bool:
    text = admin_idea_card_text(idea, author=author)
    markup = admin_idea_actions_keyboard(idea, reward_amount, queue_mode=True)
    return await notify_admin(bot, text, markup)
