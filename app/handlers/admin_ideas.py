from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards import AdminCB, CategoryToggleCB, RejectApplyCB
from app.keyboards.admin import (
    admin_back_keyboard,
    admin_cancel_keyboard,
    admin_idea_actions_keyboard,
    admin_ideas_list_keyboard,
    category_keyboard,
    reject_reasons_keyboard,
    reward_confirm_keyboard,
)
from app.repositories import ideas as ideas_repo
from app.services import admin as admin_log
from app.services import ideas as ideas_service
from app.services import rewards as rewards_service
from app.services import settings as settings_service
from app.services import users as users_service
from app.services.notifications import notify_user
from app.states.admin import AdminMessageForm, RejectReasonForm
from app.utils.pagination import clamp_page, total_pages
from app.utils.telegram import IsAdmin, safe_edit
from app.utils.text import (
    REJECT_REASON_TEXTS,
    admin_idea_card_text,
    escape_html,
)

logger = logging.getLogger(__name__)

router = Router(name="admin_ideas")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PER_PAGE = 8
NO_PENDING_TEXT = "Новых предложений нет."


def _context(callback_data: AdminCB) -> tuple[bool, int]:
    return callback_data.code == "q", callback_data.page


async def _render_card(
    callback: CallbackQuery,
    session: AsyncSession,
    idea,
    *,
    queue_mode: bool,
    back_page: int,
    extra_note: str | None = None,
) -> None:
    reward_amount = await settings_service.get_int(session, "reward_amount", 15)
    text = admin_idea_card_text(idea)
    if extra_note:
        text = f"{text}\n\n{extra_note}"
    markup = admin_idea_actions_keyboard(
        idea, reward_amount, queue_mode=queue_mode, back_page=back_page
    )
    await safe_edit(callback, text, markup)


async def _render_ideas_list(
    callback: CallbackQuery, session: AsyncSession, *, page: int, top: bool
) -> None:
    if top:
        total = await ideas_repo.count_approved(session)
        ideas = await ideas_repo.list_approved_paginated(
            session, offset=page * PER_PAGE, limit=PER_PAGE, order_by_likes=True
        )
        title = "🏆 ЛУЧШИЕ ИДЕИ (по лайкам)"
    else:
        total = await ideas_repo.count_all(session)
        ideas = await ideas_repo.list_all_paginated(
            session, offset=page * PER_PAGE, limit=PER_PAGE
        )
        title = "💡 ВСЕ ИДЕИ"

    total_pages_count = total_pages(total, PER_PAGE)
    page = clamp_page(page, total, PER_PAGE)

    if not ideas:
        await safe_edit(callback, f"{title}\n\nПока нет идей.", admin_back_keyboard())
        return

    text = (
        f"{title}\n\n"
        f"Всего: {total}\n"
        f"Страница {page + 1} из {total_pages_count}"
    )
    markup = admin_ideas_list_keyboard(
        list(ideas), page=page, total_pages_count=total_pages_count, top=top
    )
    await safe_edit(callback, text, markup)


async def _apply_rejection(
    session: AsyncSession, bot, idea, telegram_admin, reason: str
) -> None:
    admin_user = await users_service.get_current_user(session, telegram_admin)
    await ideas_service.reject_idea(
        session, idea=idea, admin_user=admin_user, reason=reason
    )
    await session.commit()
    if idea.author is not None:
        await notify_user(
            bot,
            session,
            idea.author.telegram_id,
            (
                f"❌ Твоя идея #{idea.public_number} отклонена.\n\n"
                f"Причина: {escape_html(reason)}\n\n"
                "Ты можешь предложить другую идею в любой момент."
            ),
        )


@router.callback_query(AdminCB.filter(F.action == "new_ideas"))
async def cb_new_ideas(callback: CallbackQuery, session: AsyncSession) -> None:
    idea = await ideas_repo.get_first_pending(session)
    if idea is None:
        await safe_edit(callback, NO_PENDING_TEXT, admin_back_keyboard())
    else:
        await _render_card(callback, session, idea, queue_mode=True, back_page=0)
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "next"))
async def cb_next(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    idea = await ideas_repo.get_next_pending(
        session, after_id=callback_data.entity_id
    )
    if idea is None:
        idea = await ideas_repo.get_first_pending(
            session, exclude_id=callback_data.entity_id
        )
    if idea is None:
        await safe_edit(callback, NO_PENDING_TEXT, admin_back_keyboard())
    else:
        await _render_card(callback, session, idea, queue_mode=True, back_page=0)
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "ideas"))
async def cb_all_ideas(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    await _render_ideas_list(callback, session, page=callback_data.page, top=False)
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "top_ideas"))
async def cb_top_ideas(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    await _render_ideas_list(callback, session, page=callback_data.page, top=True)
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "idea"))
async def cb_open_idea(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.entity_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return
    queue_mode, back_page = _context(callback_data)
    await _render_card(
        callback, session, idea, queue_mode=queue_mode, back_page=back_page
    )
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "approve"))
async def cb_approve(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.entity_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return
    admin_user = await users_service.get_current_user(session, callback.from_user)
    await ideas_service.approve_idea(session, idea=idea, admin_user=admin_user)
    await session.commit()
    if idea.author is not None:
        await notify_user(
            callback.bot,
            session,
            idea.author.telegram_id,
            (
                f"✅ Твоя идея #{idea.public_number} одобрена и теперь "
                "рассматривается для публикации/реализации."
            ),
        )
    queue_mode, back_page = _context(callback_data)
    await _render_card(
        callback, session, idea, queue_mode=queue_mode, back_page=back_page
    )
    await callback.answer("Идея одобрена")


@router.callback_query(AdminCB.filter(F.action == "reject"))
async def cb_reject_prompt(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.entity_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return
    queue_mode, back_page = _context(callback_data)
    await safe_edit(
        callback,
        f"❌ Выбери причину отклонения идеи #{idea.public_number}:",
        reject_reasons_keyboard(idea, queue_mode=queue_mode, back_page=back_page),
    )
    await callback.answer()


@router.callback_query(RejectApplyCB.filter())
async def cb_reject_apply(
    callback: CallbackQuery,
    callback_data: RejectApplyCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    reason_code = callback_data.reason
    idea = await ideas_repo.get_by_id(session, callback_data.idea_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return
    queue_mode = bool(callback_data.queue)
    back_page = callback_data.page

    if reason_code == "custom":
        await state.set_state(RejectReasonForm.waiting_for_custom_reason)
        await state.update_data(
            idea_id=idea.id, queue_mode=queue_mode, back_page=back_page
        )
        await safe_edit(
            callback,
            (
                f"✏️ Напиши причину отклонения идеи #{idea.public_number} "
                "одним сообщением."
            ),
            admin_cancel_keyboard(),
        )
        await callback.answer()
        return

    reason = REJECT_REASON_TEXTS.get(reason_code, "Идея не подходит.")
    await _apply_rejection(session, callback.bot, idea, callback.from_user, reason)
    await _render_card(
        callback, session, idea, queue_mode=queue_mode, back_page=back_page
    )
    await callback.answer("Идея отклонена")


@router.message(RejectReasonForm.waiting_for_custom_reason, F.text)
async def process_custom_reason(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    idea = await ideas_repo.get_by_id(session, int(data.get("idea_id", 0)))
    if idea is None:
        await state.clear()
        await message.answer("Идея не найдена.", reply_markup=admin_back_keyboard())
        return
    reason = (message.text or "").strip()
    if len(reason) < 3:
        await message.answer("Причина слишком короткая. Напиши подробнее.")
        return

    await _apply_rejection(session, message.bot, idea, message.from_user, reason)
    queue_mode = bool(data.get("queue_mode", False))
    back_page = int(data.get("back_page", 0))
    await state.clear()

    reward_amount = await settings_service.get_int(session, "reward_amount", 15)
    await message.answer(
        "✅ Идея отклонена.",
        reply_markup=admin_idea_actions_keyboard(
            idea, reward_amount, queue_mode=queue_mode, back_page=back_page
        ),
    )


@router.message(RejectReasonForm.waiting_for_custom_reason)
async def process_custom_reason_non_text(message: Message) -> None:
    await message.answer("Отправь причину текстом.")


@router.callback_query(AdminCB.filter(F.action == "hide"))
async def cb_hide(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.entity_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return
    admin_user = await users_service.get_current_user(session, callback.from_user)
    await ideas_service.hide_idea(session, idea=idea, admin_user=admin_user)
    await session.commit()
    if idea.author is not None:
        await notify_user(
            callback.bot,
            session,
            idea.author.telegram_id,
            f"🔒 Твоя идея #{idea.public_number} скрыта.",
        )
    queue_mode, back_page = _context(callback_data)
    await _render_card(
        callback, session, idea, queue_mode=queue_mode, back_page=back_page
    )
    await callback.answer("Идея скрыта")


@router.callback_query(AdminCB.filter(F.action == "message"))
async def cb_message(
    callback: CallbackQuery,
    callback_data: AdminCB,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.entity_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return
    queue_mode, back_page = _context(callback_data)
    await state.set_state(AdminMessageForm.waiting_for_text)
    await state.update_data(
        idea_id=idea.id, queue_mode=queue_mode, back_page=back_page
    )
    await safe_edit(
        callback,
        (
            f"💬 Напиши сообщение автору идеи #{idea.public_number}.\n\n"
            "Оно будет отправлено от имени администрации."
        ),
        admin_cancel_keyboard(),
    )
    await callback.answer()


@router.message(AdminMessageForm.waiting_for_text, F.text)
async def process_admin_message(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    idea = await ideas_repo.get_by_id(session, int(data.get("idea_id", 0)))
    if idea is None or idea.author is None:
        await state.clear()
        await message.answer("Идея не найдена.", reply_markup=admin_back_keyboard())
        return

    text_value = (message.text or "").strip()
    admin_user = await users_service.get_current_user(session, message.from_user)
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="message_user",
        idea_id=idea.id,
        target_user_id=idea.user_id,
        details=text_value[:500],
    )
    await session.commit()

    sent = await notify_user(
        message.bot,
        session,
        idea.author.telegram_id,
        (
            f"💬 Сообщение от администрации по идее #{idea.public_number}:\n\n"
            f"{escape_html(text_value)}"
        ),
        force=True,
    )
    queue_mode = bool(data.get("queue_mode", False))
    back_page = int(data.get("back_page", 0))
    await state.clear()

    reward_amount = await settings_service.get_int(session, "reward_amount", 15)
    note = (
        "✅ Сообщение отправлено автору."
        if sent
        else "⚠️ Не удалось отправить сообщение (автор мог заблокировать бота)."
    )
    await message.answer(
        note,
        reply_markup=admin_idea_actions_keyboard(
            idea, reward_amount, queue_mode=queue_mode, back_page=back_page
        ),
    )


@router.message(AdminMessageForm.waiting_for_text)
async def process_admin_message_non_text(message: Message) -> None:
    await message.answer("Отправь сообщение текстом.")


@router.callback_query(AdminCB.filter(F.action == "reward"))
async def cb_reward_prompt(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.entity_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return
    reward_amount = await settings_service.get_int(session, "reward_amount", 15)
    queue_mode, back_page = _context(callback_data)
    await safe_edit(
        callback,
        (
            "⭐ ОБРАБОТКА НАГРАДЫ\n\n"
            f"Вы действительно хотите обработать награду {reward_amount} ⭐ "
            f"для автора идеи #{idea.public_number}?"
        ),
        reward_confirm_keyboard(idea, queue_mode=queue_mode, back_page=back_page),
    )
    await callback.answer()


@router.callback_query(AdminCB.filter(F.action == "reward_confirm"))
async def cb_reward_confirm(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.entity_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return
    admin_user = await users_service.get_current_user(session, callback.from_user)
    reward_amount = await settings_service.get_int(session, "reward_amount", 15)
    gift_id = await settings_service.get_value(session, "reward_gift_id", "")

    outcome = await rewards_service.grant_reward(
        session,
        bot=callback.bot,
        idea=idea,
        admin_user=admin_user,
        amount=reward_amount,
        gift_id=gift_id or None,
    )
    await session.commit()

    if outcome.user_message and idea.author is not None:
        await notify_user(
            callback.bot,
            session,
            idea.author.telegram_id,
            outcome.user_message,
            force=True,
        )

    queue_mode, back_page = _context(callback_data)
    await _render_card(
        callback,
        session,
        idea,
        queue_mode=queue_mode,
        back_page=back_page,
        extra_note=outcome.admin_message,
    )
    await callback.answer("Готово")


@router.callback_query(AdminCB.filter(F.action == "category"))
async def cb_category(
    callback: CallbackQuery, callback_data: AdminCB, session: AsyncSession
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.entity_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return
    categories = list(await ideas_repo.list_categories(session))
    assigned = await ideas_repo.get_assigned_category_ids(session, idea.id)
    queue_mode, back_page = _context(callback_data)
    await safe_edit(
        callback,
        (
            f"🏷 Категории идеи #{idea.public_number}\n\n"
            "Нажми на категорию, чтобы назначить или снять её."
        ),
        category_keyboard(
            idea,
            categories,
            assigned,
            queue_mode=queue_mode,
            back_page=back_page,
        ),
    )
    await callback.answer()


@router.callback_query(CategoryToggleCB.filter())
async def cb_category_toggle(
    callback: CallbackQuery,
    callback_data: CategoryToggleCB,
    session: AsyncSession,
) -> None:
    idea = await ideas_repo.get_by_id(session, callback_data.idea_id)
    if idea is None:
        await callback.answer("Идея не найдена.", show_alert=True)
        return

    assigned_now = await ideas_repo.toggle_category(
        session, idea_id=idea.id, category_id=callback_data.category_id
    )
    admin_user = await users_service.get_current_user(session, callback.from_user)
    await admin_log.log_action(
        session,
        admin_id=admin_user.id,
        action="category_change",
        idea_id=idea.id,
        details=(
            f"Категория #{callback_data.category_id} "
            f"{'назначена' if assigned_now else 'снята'} для идеи #{idea.public_number}"
        ),
    )
    await session.commit()

    categories = list(await ideas_repo.list_categories(session))
    assigned = await ideas_repo.get_assigned_category_ids(session, idea.id)
    queue_mode = bool(callback_data.queue)
    back_page = callback_data.page
    await safe_edit(
        callback,
        (
            f"🏷 Категории идеи #{idea.public_number}\n\n"
            "Нажми на категорию, чтобы назначить или снять её."
        ),
        category_keyboard(
            idea,
            categories,
            assigned,
            queue_mode=queue_mode,
            back_page=back_page,
        ),
    )
    await callback.answer("Обновлено")
