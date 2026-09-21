from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

ASYNC_DRIVER = "postgresql+asyncpg"
_TRUE_VALUES = {"true", "1", "yes", "on"}

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _unique_statement_name() -> str:
    """pgbouncer multiplexes server connections, so statement names must be unique."""
    return f"__asyncpg_{uuid4()}__"


def build_async_url(raw_url: str) -> tuple[URL, dict[str, Any]]:
    """Converts a plain postgresql:// URL into an asyncpg URL.

    The Supabase pooler URL contains the ``pgbouncer=true`` flag which asyncpg
    does not understand. It is removed from the URL and translated into
    ``statement_cache_size=0``, ``prepared_statement_cache_size=0`` and
    ``prepared_statement_name_func`` — prepared statements must be disabled or
    uniquely named in transaction pooling mode.
    """
    url = make_url(raw_url)
    if url.drivername in {"postgresql", "postgres"}:
        url = url.set(drivername=ASYNC_DRIVER)

    query = dict(url.query)
    connect_args: dict[str, Any] = {}
    pgbouncer = str(query.pop("pgbouncer", "")).lower()
    if pgbouncer in _TRUE_VALUES:
        connect_args["statement_cache_size"] = 0
        connect_args["prepared_statement_cache_size"] = 0
        connect_args["prepared_statement_name_func"] = _unique_statement_name

    url = url.set(query=query)
    return url, connect_args


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        url, connect_args = build_async_url(settings.database_url)
        _engine = create_async_engine(
            url,
            pool_size=10,
            max_overflow=10,
            pool_recycle=1800,
            connect_args=connect_args,
        )
        logger.info("Database engine created")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def dispose_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database engine disposed")


class DatabaseSessionMiddleware(BaseMiddleware):
    """Opens one AsyncSession per update and commits it after the handler."""

    async def __call__(
        self, handler: Any, event: TelegramObject, data: dict[str, Any]
    ) -> Any:
        factory = get_session_factory()
        async with factory() as session:
            data["session"] = session
            try:
                result = await handler(event, data)
                if session.in_transaction():
                    await session.commit()
                return result
            except Exception:
                await session.rollback()
                raise
