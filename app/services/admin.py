from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import AdminAction


async def log_action(
    session: AsyncSession,
    *,
    admin_id: int | None,
    action: str,
    idea_id: int | None = None,
    target_user_id: int | None = None,
    details: str | None = None,
) -> None:
    session.add(
        AdminAction(
            admin_id=admin_id,
            action=action,
            idea_id=idea_id,
            target_user_id=target_user_id,
            details=details,
        )
    )
    await session.flush()
