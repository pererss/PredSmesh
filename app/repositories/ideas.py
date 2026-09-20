from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Idea, IdeaCategory, IdeaStatus

PUBLIC_NUMBER_SEQUENCE = "ideas_public_number_seq"


async def next_public_number(session: AsyncSession) -> int:
    value = await session.scalar(
        text(f"SELECT nextval('{PUBLIC_NUMBER_SEQUENCE}')")
    )
    return int(value)


async def create(
    session: AsyncSession, *, user_id: int, text_value: str, public_number: int
) -> Idea:
    idea = Idea(
        public_number=public_number,
        user_id=user_id,
        text=text_value,
        status=IdeaStatus.PENDING,
    )
    session.add(idea)
    await session.flush()
    return idea


async def get_by_id(session: AsyncSession, idea_id: int) -> Idea | None:
    return await session.get(Idea, idea_id)


async def get_by_public_number(
    session: AsyncSession, public_number: int
) -> Idea | None:
    return await session.scalar(
        select(Idea).where(Idea.public_number == public_number)
    )


async def get_first_pending(
    session: AsyncSession, *, exclude_id: int | None = None
) -> Idea | None:
    stmt = select(Idea).where(Idea.status == IdeaStatus.PENDING)
    if exclude_id is not None:
        stmt = stmt.where(Idea.id != exclude_id)
    return await session.scalar(stmt.order_by(Idea.id).limit(1))


async def get_next_pending(session: AsyncSession, *, after_id: int) -> Idea | None:
    return await session.scalar(
        select(Idea)
        .where(Idea.status == IdeaStatus.PENDING, Idea.id > after_id)
        .order_by(Idea.id)
        .limit(1)
    )


async def list_pending_paginated(
    session: AsyncSession, *, offset: int, limit: int
) -> Sequence[Idea]:
    result = await session.scalars(
        select(Idea)
        .where(Idea.status == IdeaStatus.PENDING)
        .order_by(Idea.created_at.desc(), Idea.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.all()


async def list_all_paginated(
    session: AsyncSession, *, offset: int, limit: int
) -> Sequence[Idea]:
    result = await session.scalars(
        select(Idea)
        .order_by(Idea.created_at.desc(), Idea.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.all()


async def list_all_with_authors(session: AsyncSession) -> Sequence[Idea]:
    result = await session.scalars(
        select(Idea).order_by(Idea.public_number.asc())
    )
    return result.all()


async def list_approved_paginated(
    session: AsyncSession, *, offset: int, limit: int, order_by_likes: bool = False
) -> Sequence[Idea]:
    stmt = select(Idea).where(Idea.status == IdeaStatus.APPROVED)
    if order_by_likes:
        stmt = stmt.order_by(Idea.likes_count.desc(), Idea.created_at.desc(), Idea.id.desc())
    else:
        stmt = stmt.order_by(Idea.created_at.desc(), Idea.id.desc())
    result = await session.scalars(stmt.offset(offset).limit(limit))
    return result.all()


async def list_by_user(
    session: AsyncSession, *, user_id: int, offset: int, limit: int
) -> Sequence[Idea]:
    result = await session.scalars(
        select(Idea)
        .where(Idea.user_id == user_id)
        .order_by(Idea.created_at.desc(), Idea.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return result.all()


async def get_random_approved(session: AsyncSession) -> Idea | None:
    return await session.scalar(
        select(Idea)
        .where(Idea.status == IdeaStatus.APPROVED)
        .order_by(func.random())
        .limit(1)
    )


async def count_by_status(session: AsyncSession, status: IdeaStatus) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Idea).where(Idea.status == status)
        )
        or 0
    )


async def count_by_status_for_user(
    session: AsyncSession, user_id: int
) -> dict[IdeaStatus, int]:
    rows = await session.execute(
        select(Idea.status, func.count())
        .where(Idea.user_id == user_id)
        .group_by(Idea.status)
    )
    return {status: int(count) for status, count in rows.all()}


async def count_all(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(Idea)) or 0)


async def count_approved(session: AsyncSession) -> int:
    return await count_by_status(session, IdeaStatus.APPROVED)


async def count_by_user(session: AsyncSession, user_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Idea).where(Idea.user_id == user_id)
        )
        or 0
    )


async def count_created_since(session: AsyncSession, since: datetime) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Idea).where(Idea.created_at >= since)
        )
        or 0
    )


async def count_approved_since(session: AsyncSession, since: datetime) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Idea)
            .where(Idea.approved_at.is_not(None), Idea.approved_at >= since)
        )
        or 0
    )


async def count_rejected_since(session: AsyncSession, since: datetime) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Idea)
            .where(
                Idea.status == IdeaStatus.REJECTED,
                Idea.updated_at >= since,
            )
        )
        or 0
    )


async def sum_likes(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.coalesce(func.sum(Idea.likes_count), 0))) or 0)


async def sum_views(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.coalesce(func.sum(Idea.views_count), 0))) or 0)


async def increment_views(session: AsyncSession, idea_id: int) -> None:
    await session.execute(
        text("UPDATE ideas SET views_count = views_count + 1 WHERE id = :idea_id"),
        {"idea_id": idea_id},
    )


async def set_status(session: AsyncSession, idea: Idea, status: IdeaStatus) -> None:
    idea.status = status
    await session.flush()


async def list_categories(session: AsyncSession) -> Sequence:
    from app.database.models import Category

    result = await session.scalars(select(Category).order_by(Category.id))
    return result.all()


async def get_assigned_category_ids(
    session: AsyncSession, idea_id: int
) -> set[int]:
    rows = await session.scalars(
        select(IdeaCategory.category_id).where(IdeaCategory.idea_id == idea_id)
    )
    return set(rows.all())


async def toggle_category(
    session: AsyncSession, *, idea_id: int, category_id: int
) -> bool:
    existing = await session.scalar(
        select(IdeaCategory).where(
            IdeaCategory.idea_id == idea_id,
            IdeaCategory.category_id == category_id,
        )
    )
    if existing is not None:
        await session.delete(existing)
        await session.flush()
        return False
    session.add(IdeaCategory(idea_id=idea_id, category_id=category_id))
    await session.flush()
    return True
