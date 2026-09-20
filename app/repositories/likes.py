from __future__ import annotations

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Idea, Like


async def is_liked(session: AsyncSession, *, idea_id: int, user_id: int) -> bool:
    like_id = await session.scalar(
        select(Like.id).where(Like.idea_id == idea_id, Like.user_id == user_id)
    )
    return like_id is not None


async def count_for_idea(session: AsyncSession, idea_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Like).where(Like.idea_id == idea_id)
        )
        or 0
    )


async def count_total(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(Like)) or 0)


async def toggle(
    session: AsyncSession, *, idea_id: int, user_id: int
) -> tuple[bool, int]:
    """Adds or removes a like and returns (liked_now, likes_count).

    The ``likes`` table is the source of truth: the counter on the idea is
    recalculated from it inside the same transaction.
    """
    result = await session.execute(
        delete(Like).where(Like.idea_id == idea_id, Like.user_id == user_id)
    )
    liked = False
    if result.rowcount == 0:
        try:
            async with session.begin_nested():
                session.add(Like(idea_id=idea_id, user_id=user_id))
                await session.flush()
        except IntegrityError:
            liked = True
        else:
            liked = True

    likes_count = await count_for_idea(session, idea_id)
    await session.execute(
        update(Idea).where(Idea.id == idea_id).values(likes_count=likes_count)
    )
    return liked, likes_count
