from __future__ import annotations

from aiogram.types import User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.base import utcnow
from app.database.models import Idea, IdeaStatus, User
from app.repositories import ideas as ideas_repo
from app.repositories import likes as likes_repo
from app.services import admin as admin_log
from app.services import settings as settings_service
from app.services import users as users_service
from app.utils.text import MAX_IDEA_TEXT_LENGTH, MIN_IDEA_TEXT_LENGTH


class IdeaValidationError(Exception):
    pass


class SubmissionsDisabledError(Exception):
    pass


def validate_idea_text(text_value: str) -> str:
    cleaned = text_value.strip()
    if len(cleaned) < MIN_IDEA_TEXT_LENGTH:
        raise IdeaValidationError("Опиши идею немного подробнее.")
    if len(cleaned) > MAX_IDEA_TEXT_LENGTH:
        raise IdeaValidationError(
            f"Идея слишком длинная. Максимум {MAX_IDEA_TEXT_LENGTH} символов."
        )
    return cleaned


async def submit_idea(
    session: AsyncSession, *, telegram_user: TelegramUser, text_value: str
) -> tuple[Idea, User]:
    cleaned = validate_idea_text(text_value)
    enabled = await settings_service.get_bool(session, "submissions_enabled", True)
    if not enabled:
        raise SubmissionsDisabledError("Приём идей временно приостановлен.")
    user = await users_service.get_current_user(session, telegram_user)
    public_number = await ideas_repo.next_public_number(session)
    idea = await ideas_repo.create(
        session, user_id=user.id, text_value=cleaned, public_number=public_number
    )
    return idea, user


async def approve_idea(session: AsyncSession, *, idea: Idea, admin_user: User) -> None:
    idea.status = IdeaStatus.APPROVED
    idea.approved_at = utcnow()
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="approve",
        idea_id=idea.id,
        target_user_id=idea.user_id,
        details=f"Идея #{idea.public_number} одобрена",
    )
    await session.flush()


async def reject_idea(
    session: AsyncSession, *, idea: Idea, admin_user: User, reason: str
) -> None:
    idea.status = IdeaStatus.REJECTED
    idea.rejection_reason = reason
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="reject",
        idea_id=idea.id,
        target_user_id=idea.user_id,
        details=f"Идея #{idea.public_number} отклонена. Причина: {reason}",
    )
    await session.flush()


async def hide_idea(session: AsyncSession, *, idea: Idea, admin_user: User) -> None:
    idea.status = IdeaStatus.HIDDEN
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="hide",
        idea_id=idea.id,
        target_user_id=idea.user_id,
        details=f"Идея #{idea.public_number} скрыта",
    )
    await session.flush()


async def toggle_like(session: AsyncSession, *, idea: Idea, user: User) -> tuple[bool, int]:
    liked, likes_count = await likes_repo.toggle(
        session, idea_id=idea.id, user_id=user.id
    )
    idea.likes_count = likes_count
    return liked, likes_count


async def register_view(session: AsyncSession, *, idea: Idea) -> None:
    await ideas_repo.increment_views(session, idea.id)
    idea.views_count += 1
