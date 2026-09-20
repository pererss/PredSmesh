from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramConflictError,
    TelegramUnauthorizedError,
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from sqlalchemy import text

from app.config import get_settings
from app.database.session import (
    DatabaseSessionMiddleware,
    dispose_engine,
    get_session_factory,
)
from app.handlers import (
    admin,
    admin_broadcast,
    admin_ideas,
    admin_rewards,
    admin_settings,
    admin_users,
    catalog,
    ideas,
    profile,
    referrals,
    start,
    user,
)
from app.handlers.user import on_error
from app.logging_config import setup_logging
from app.services import settings as settings_service

logger = logging.getLogger(__name__)

POLLING_RETRY_DELAY = 5


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())

    database_middleware = DatabaseSessionMiddleware()
    dp.message.middleware(database_middleware)
    dp.callback_query.middleware(database_middleware)

    dp.include_router(start.router)
    dp.include_router(ideas.router)
    dp.include_router(catalog.router)
    dp.include_router(profile.router)
    dp.include_router(referrals.router)
    dp.include_router(admin.router)
    dp.include_router(admin_ideas.router)
    dp.include_router(admin_users.router)
    dp.include_router(admin_rewards.router)
    dp.include_router(admin_broadcast.router)
    dp.include_router(admin_settings.router)
    dp.include_router(user.router)

    dp.errors.register(on_error)
    return dp


async def register_commands(bot: Bot, admin_id: int) -> None:
    default_commands = [
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="menu", description="Меню"),
        BotCommand(command="myideas", description="Мои предложения"),
        BotCommand(command="help", description="Как это работает"),
    ]
    await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())

    admin_commands = [
        *default_commands,
        BotCommand(command="admin", description="Админ-панель"),
    ]
    try:
        await bot.set_my_commands(
            admin_commands, scope=BotCommandScopeChat(chat_id=admin_id)
        )
    except TelegramAPIError as exc:
        logger.warning("Failed to set admin commands: %s", exc)


async def check_database() -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(text("SELECT 1"))
        await settings_service.ensure_defaults(
            session, get_settings().reward_amount
        )
        await session.commit()


def _mask_proxy(proxy: str) -> str:
    if "@" not in proxy:
        return proxy
    if "://" in proxy:
        scheme, rest = proxy.split("://", 1)
        return f"{scheme}://***@{rest.rsplit('@', 1)[1]}"
    return f"***@{proxy.rsplit('@', 1)[1]}"


async def run_polling(dispatcher: Dispatcher, bot: Bot) -> None:
    allowed_updates = dispatcher.resolve_used_update_types()
    while True:
        try:
            await dispatcher.start_polling(bot, allowed_updates=allowed_updates)
            return
        except (TelegramConflictError, TelegramUnauthorizedError):
            raise
        except Exception as exc:  # noqa: BLE001 - keep the bot alive on network/proxy errors
            logger.warning(
                "Polling stopped with error: %s. Reconnecting in %s seconds",
                exc,
                POLLING_RETRY_DELAY,
            )
            await asyncio.sleep(POLLING_RETRY_DELAY)


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Starting bot (env=%s)", settings.app_env)

    session = (
        AiohttpSession(proxy=settings.telegram_proxy)
        if settings.telegram_proxy
        else None
    )
    if settings.telegram_proxy:
        logger.info("Using Telegram proxy: %s", _mask_proxy(settings.telegram_proxy))

    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML, link_preview_is_disabled=True
        ),
    )
    dispatcher = build_dispatcher()

    try:
        await check_database()
        logger.info("Database connection established")
    except Exception:
        logger.exception(
            "Database check failed. "
            "Did you run supabase_schema.sql or alembic upgrade head?"
        )
        await bot.session.close()
        await dispose_engine()
        raise SystemExit(1) from None

    try:
        await register_commands(bot, settings.admin_id)
    except Exception as exc:  # noqa: BLE001 - startup must not crash on network issues
        logger.warning("Failed to register bot commands: %s", exc)

    try:
        me = await bot.get_me()
        logger.info("Authorized as @%s (id=%s)", me.username, me.id)
    except Exception as exc:  # noqa: BLE001 - startup must not crash on network issues
        logger.warning("Failed to fetch bot info: %s", exc)

    try:
        await run_polling(dispatcher, bot)
    finally:
        await bot.session.close()
        await dispose_engine()
        logger.info("Bot stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
