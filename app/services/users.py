from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.repositories import users as users_repo


async def get_current_user(
    session: AsyncSession, telegram_user: TelegramUser
) -> User:
    return await users_repo.get_or_create(
        session,
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )
