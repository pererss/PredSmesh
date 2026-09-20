from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Setting
from app.utils.text import parse_bool

DEFAULT_SETTINGS: dict[str, str] = {
    "reward_amount": "15",
    "submissions_enabled": "true",
    "notifications_enabled": "true",
    "reward_gift_id": "",
}


async def ensure_defaults(
    session: AsyncSession, default_reward_amount: int = 15
) -> None:
    values = dict(DEFAULT_SETTINGS)
    values["reward_amount"] = str(default_reward_amount)
    stmt = (
        pg_insert(Setting)
        .values([{"key": key, "value": value} for key, value in values.items()])
        .on_conflict_do_nothing(index_elements=["key"])
    )
    await session.execute(stmt)


async def get_all(session: AsyncSession) -> dict[str, str]:
    rows = (await session.execute(select(Setting.key, Setting.value))).all()
    values = dict(DEFAULT_SETTINGS)
    values.update({key: value for key, value in rows})
    return values


async def get_value(session: AsyncSession, key: str, default: str = "") -> str:
    value = await session.scalar(select(Setting.value).where(Setting.key == key))
    if value is None:
        return DEFAULT_SETTINGS.get(key, default)
    return value


async def get_int(session: AsyncSession, key: str, default: int) -> int:
    raw = await get_value(session, key, str(default))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


async def get_bool(session: AsyncSession, key: str, default: bool) -> bool:
    raw = await get_value(session, key, "true" if default else "false")
    return parse_bool(raw, default)


async def set_value(session: AsyncSession, key: str, value: str) -> None:
    stmt = (
        pg_insert(Setting)
        .values(key=key, value=value)
        .on_conflict_do_update(index_elements=["key"], set_={"value": value})
    )
    await session.execute(stmt)
