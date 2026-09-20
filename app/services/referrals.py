from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.repositories import users as users_repo


def build_referral_link(bot_username: str, telegram_id: int) -> str:
    return f"https://t.me/{bot_username}?start=ref_{telegram_id}"


async def register_referral(
    session: AsyncSession,
    *,
    referred_user: User,
    referrer_telegram_id: int,
) -> User | None:
    if referrer_telegram_id == referred_user.telegram_id:
        return None
    if referred_user.referrer_id is not None:
        return None
    referrer = await users_repo.get_by_telegram_id(session, referrer_telegram_id)
    if referrer is None:
        return None
    created = await users_repo.create_referral(
        session, referrer_id=referrer.id, referred_id=referred_user.id
    )
    if not created:
        return None
    referred_user.referrer_id = referrer.id
    await session.flush()
    return referrer


async def count_referrals(session: AsyncSession, referrer_id: int) -> int:
    return await users_repo.count_referrals(session, referrer_id)
