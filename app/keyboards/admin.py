from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup

from app.database.models import Category, Idea, IdeaStatus, Reward
from app.keyboards import (
    AdminCB,
    CategoryToggleCB,
    RejectApplyCB,
    cb_button,
)
from app.keyboards.pagination import pagination_buttons
from app.utils.text import (
    REJECT_REASONS,
    STATUS_LABELS,
    parse_bool,
)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            cb_button("📥 Новые предложения", AdminCB(action="new_ideas")),
            cb_button("💡 Все идеи", AdminCB(action="ideas")),
        ],
        [
            cb_button("🏆 Лучшие идеи", AdminCB(action="top_ideas")),
            cb_button("👥 Пользователи", AdminCB(action="users")),
        ],
        [
            cb_button("⭐ Награды", AdminCB(action="rewards")),
            cb_button("📊 Статистика", AdminCB(action="stats")),
        ],
        [
            cb_button("📢 Рассылка", AdminCB(action="broadcast")),
            cb_button("⚙️ Настройки", AdminCB(action="settings")),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_back_keyboard() -> InlineKeyboardMarkup:
    rows = [[cb_button("🔙 Админ-панель", AdminCB(action="panel"))]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    rows = [[cb_button("❌ Отмена", AdminCB(action="panel"))]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_idea_actions_keyboard(
    idea: Idea,
    reward_amount: int,
    *,
    queue_mode: bool = False,
    back_page: int = 0,
) -> InlineKeyboardMarkup:
    ctx = "q" if queue_mode else "l"
    rows: list[list] = []

    first_row = []
    if idea.status == IdeaStatus.PENDING:
        first_row.append(
            cb_button(
                "✅ Одобрить",
                AdminCB(action="approve", entity_id=idea.id, page=back_page, code=ctx),
            )
        )
    if idea.status in {IdeaStatus.PENDING, IdeaStatus.APPROVED}:
        first_row.append(
            cb_button(
                f"⭐ Наградить {reward_amount} ⭐",
                AdminCB(action="reward", entity_id=idea.id, page=back_page, code=ctx),
            )
        )
    if first_row:
        rows.append(first_row)

    second_row = []
    if idea.status in {IdeaStatus.PENDING, IdeaStatus.APPROVED}:
        second_row.append(
            cb_button(
                "❌ Отклонить",
                AdminCB(action="reject", entity_id=idea.id, page=back_page, code=ctx),
            )
        )
    second_row.append(
        cb_button(
            "💬 Написать автору",
            AdminCB(action="message", entity_id=idea.id, page=back_page, code=ctx),
        )
    )
    rows.append(second_row)

    third_row = []
    if idea.status in {IdeaStatus.PENDING, IdeaStatus.APPROVED}:
        third_row.append(
            cb_button(
                "🔒 Скрыть",
                AdminCB(action="hide", entity_id=idea.id, page=back_page, code=ctx),
            )
        )
    third_row.append(
        cb_button(
            "🏷 Категория",
            AdminCB(action="category", entity_id=idea.id, page=back_page, code=ctx),
        )
    )
    rows.append(third_row)

    if queue_mode:
        rows.append(
            [cb_button("➡️ Следующее", AdminCB(action="next", entity_id=idea.id))]
        )
    else:
        rows.append(
            [cb_button("🔙 К списку идей", AdminCB(action="ideas", page=back_page))]
        )
    rows.append([cb_button("🛠 Админ-панель", AdminCB(action="panel"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reject_reasons_keyboard(
    idea: Idea, *, queue_mode: bool = False, back_page: int = 0
) -> InlineKeyboardMarkup:
    ctx = "q" if queue_mode else "l"
    rows: list[list] = []
    pair: list = []
    for code, label in REJECT_REASONS:
        pair.append(
            cb_button(
                label,
                RejectApplyCB(
                    idea_id=idea.id,
                    reason=code,
                    queue=1 if queue_mode else 0,
                    page=back_page,
                ),
            )
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append(
        [
            cb_button(
                "🔙 Назад",
                AdminCB(action="idea", entity_id=idea.id, page=back_page, code=ctx),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reward_confirm_keyboard(
    idea: Idea, *, queue_mode: bool = False, back_page: int = 0
) -> InlineKeyboardMarkup:
    ctx = "q" if queue_mode else "l"
    rows = [
        [
            cb_button(
                "✅ Подтвердить",
                AdminCB(
                    action="reward_confirm",
                    entity_id=idea.id,
                    page=back_page,
                    code=ctx,
                ),
            )
        ],
        [
            cb_button(
                "❌ Отмена",
                AdminCB(action="idea", entity_id=idea.id, page=back_page, code=ctx),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def category_keyboard(
    idea: Idea,
    categories: list[Category],
    assigned_ids: set[int],
    *,
    queue_mode: bool = False,
    back_page: int = 0,
) -> InlineKeyboardMarkup:
    ctx = "q" if queue_mode else "l"
    rows: list[list] = []
    pair: list = []
    for category in categories:
        mark = "✅" if category.id in assigned_ids else "▫️"
        pair.append(
            cb_button(
                f"{mark} {category.name}",
                CategoryToggleCB(
                    idea_id=idea.id,
                    category_id=category.id,
                    queue=1 if queue_mode else 0,
                    page=back_page,
                ),
            )
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append(
        [
            cb_button(
                "🔙 К идее",
                AdminCB(action="idea", entity_id=idea.id, page=back_page, code=ctx),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_ideas_list_keyboard(
    ideas: list[Idea], *, page: int, total_pages_count: int, top: bool
) -> InlineKeyboardMarkup:
    action = "top_ideas" if top else "ideas"
    rows: list[list] = []
    for idea in ideas:
        rows.append(
            [
                cb_button(
                    f"💡 #{idea.public_number} • {STATUS_LABELS.get(idea.status, idea.status)}",
                    AdminCB(action="idea", entity_id=idea.id, page=page, code="l"),
                )
            ]
        )
    nav = pagination_buttons(
        page=page,
        total_pages_count=total_pages_count,
        prev_callback=AdminCB(action=action, page=page - 1),
        next_callback=AdminCB(action=action, page=page + 1),
    )
    if nav:
        rows.append(nav)
    rows.append([cb_button("🛠 Админ-панель", AdminCB(action="panel"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_users_list_keyboard(
    users: list, *, page: int, total_pages_count: int
) -> InlineKeyboardMarkup:
    rows: list[list] = []
    for user in users:
        if user.username:
            name = f"@{user.username}"
        else:
            name = user.first_name or f"ID {user.telegram_id}"
        rows.append(
            [
                cb_button(
                    f"👤 {name}",
                    AdminCB(action="user", entity_id=user.id, page=page),
                )
            ]
        )
    nav = pagination_buttons(
        page=page,
        total_pages_count=total_pages_count,
        prev_callback=AdminCB(action="users", page=page - 1),
        next_callback=AdminCB(action="users", page=page + 1),
    )
    if nav:
        rows.append(nav)
    rows.append([cb_button("🛠 Админ-панель", AdminCB(action="panel"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_user_card_keyboard(page: int) -> InlineKeyboardMarkup:
    rows = [
        [cb_button("🔙 К пользователям", AdminCB(action="users", page=page))],
        [cb_button("🛠 Админ-панель", AdminCB(action="panel"))],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_rewards_list_keyboard(
    rewards: list[Reward], *, status_filter: str, page: int, total_pages_count: int
) -> InlineKeyboardMarkup:
    rows: list[list] = [
        [
            cb_button("Все", AdminCB(action="rewards", code="all")),
            cb_button("⏳ Pending", AdminCB(action="rewards", code="pending")),
            cb_button("🛠 Manual", AdminCB(action="rewards", code="manual")),
        ],
        [
            cb_button("✅ Completed", AdminCB(action="rewards", code="completed")),
            cb_button("❌ Failed", AdminCB(action="rewards", code="failed")),
        ],
    ]
    for reward in rewards:
        if reward.status.value in {"MANUAL", "PENDING"}:
            rows.append(
                [
                    cb_button(
                        f"✅ #{reward.id} отметить выполненной",
                        AdminCB(
                            action="reward_done",
                            entity_id=reward.id,
                            page=page,
                            code=status_filter,
                        ),
                    )
                ]
            )
    nav = pagination_buttons(
        page=page,
        total_pages_count=total_pages_count,
        prev_callback=AdminCB(action="rewards", page=page - 1, code=status_filter),
        next_callback=AdminCB(action="rewards", page=page + 1, code=status_filter),
    )
    if nav:
        rows.append(nav)
    rows.append([cb_button("🛠 Админ-панель", AdminCB(action="panel"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_settings_keyboard(values: dict[str, str]) -> InlineKeyboardMarkup:
    reward_amount = values.get("reward_amount", "15")
    submissions = (
        "✅ Включён"
        if parse_bool(values.get("submissions_enabled"), True)
        else "⛔ Выключен"
    )
    notifications = (
        "✅ Включены"
        if parse_bool(values.get("notifications_enabled"), True)
        else "⛔ Выключены"
    )
    gift_id = values.get("reward_gift_id") or "—"
    rows = [
        [
            cb_button(
                f"💰 Награда: {reward_amount} ⭐ ✏️",
                AdminCB(action="setting_edit", code="reward_amount"),
            )
        ],
        [
            cb_button(
                f"📥 Приём идей: {submissions}",
                AdminCB(action="setting_toggle", code="submissions_enabled"),
            )
        ],
        [
            cb_button(
                f"🔔 Уведомления: {notifications}",
                AdminCB(action="setting_toggle", code="notifications_enabled"),
            )
        ],
        [
            cb_button(
                f"🎁 Gift ID: {gift_id} ✏️",
                AdminCB(action="setting_edit", code="reward_gift_id"),
            )
        ],
        [cb_button("🛠 Админ-панель", AdminCB(action="panel"))],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def broadcast_preview_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            cb_button("📤 Отправить", AdminCB(action="broadcast_send")),
            cb_button("❌ Отмена", AdminCB(action="broadcast_cancel")),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
