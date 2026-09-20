from __future__ import annotations

import html
from datetime import datetime

from app.database.models import IdeaStatus, RewardStatus, User

MIN_IDEA_TEXT_LENGTH = 20
MAX_IDEA_TEXT_LENGTH = 5000

MAIN_MENU_TEXT = """💡 ПРИДУМАЙ. ПРЕДЛОЖИ. ЗАПУСТИ.

Есть идея стартапа, сервиса, бота или сайта, который ты давно хотел создать, но так и не сделал?

Расскажи о ней нам.

Возможно, именно твоя идея станет основой нового проекта.

За интересные и качественные предложения мы можем отправить автору {reward} ⭐ Telegram Stars.

Выбери действие ниже 👇"""

HOW_IT_WORKS_TEXT = """❓ КАК ВСЁ РАБОТАЕТ

1. Ты отправляешь свою идею.

2. Мы рассматриваем предложения.

3. Интересные идеи попадают в каталог.

4. Если идея подходит для реализации, мы связываемся с автором.

5. За выбранную идею можно получить {reward} ⭐ Stars.

💡 Идея не обязана быть полностью проработанной. Главное — чтобы в ней был интересный смысл или решение проблемы.

⚠️ Отправляй только собственные идеи и не присылай чужие материалы."""

IDEA_SUBMISSION_PROMPT = """💡 ПРЕДЛОЖЕНИЕ ИДЕИ

Расскажи, какой стартап, сайт, бот, сервис или другой интернет-проект ты хотел бы создать.

Можно описать даже сырую идею — тебе не обязательно иметь готовый бизнес-план.

Напиши одним сообщением:

- что это;
- для кого;
- какую проблему решает;
- почему это может быть интересно.

📝 Напиши свою идею ниже."""

IDEA_CONFIRMATION_TEXT = """✅ ИДЕЯ ПОЛУЧЕНА!

Спасибо, я передал её на рассмотрение.

Если идея будет выбрана, мы свяжемся с тобой здесь и отправим {reward} ⭐ Stars.

Номер предложения: #{number}"""

STATUS_LABELS: dict[IdeaStatus, str] = {
    IdeaStatus.PENDING: "📥 На рассмотрении",
    IdeaStatus.APPROVED: "✅ Одобрено",
    IdeaStatus.REJECTED: "❌ Отклонено",
    IdeaStatus.REWARDED: "⭐ Награждено",
    IdeaStatus.HIDDEN: "🔒 Скрыто",
}

REWARD_STATUS_LABELS: dict[RewardStatus, str] = {
    RewardStatus.PENDING: "⏳ Ожидает",
    RewardStatus.COMPLETED: "✅ Выполнена",
    RewardStatus.FAILED: "❌ Ошибка",
    RewardStatus.MANUAL: "🛠 Ручная обработка",
}

REJECT_REASONS: tuple[tuple[str, str], ...] = (
    ("not_suitable", "❌ Не подходит"),
    ("too_raw", "📝 Слишком сырая идея"),
    ("exists", "🔁 Уже существует"),
    ("spam", "📢 Реклама/спам"),
    ("rules", "⚠️ Нарушение правил"),
    ("custom", "✏️ Своя причина"),
)

REJECT_REASON_TEXTS: dict[str, str] = {
    "not_suitable": "Идея не подходит для нашего проекта.",
    "too_raw": "Идея слишком сырая и требует более детальной проработки.",
    "exists": "Похожая идея уже существует или была предложена ранее.",
    "spam": "Предложение похоже на рекламу или спам.",
    "rules": "Нарушение правил проекта.",
}


def escape_html(value: str) -> str:
    return html.escape(value, quote=False)


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"true", "1", "yes", "on", "вкл", "включён", "включен"}


def truncate(value: str, limit: int) -> str:
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def format_date(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y")


def format_datetime(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.strftime("%d.%m.%Y %H:%M")


def status_label(status: IdeaStatus) -> str:
    return STATUS_LABELS.get(status, str(status))


def reward_status_label(status: RewardStatus) -> str:
    return REWARD_STATUS_LABELS.get(status, str(status))


def author_display(user: User | None) -> str:
    if user is None:
        return "неизвестно"
    if user.username:
        return f"@{escape_html(user.username)}"
    name = escape_html(user.first_name or "Без имени")
    return f"{name} (ID: {user.telegram_id})"


def admin_idea_card_text(
    idea, *, header: str | None = None, author: User | None = None
) -> str:
    author = author or idea.author
    if header is None:
        header = "📥 НОВОЕ ПРЕДЛОЖЕНИЕ" if idea.status == IdeaStatus.PENDING else "💡 ИДЕЯ"
    lines = [
        f"{header} #{idea.public_number}",
        "",
        f"👤 Автор: {author_display(author)}",
        f"🆔 ID: {author.telegram_id if author else '—'}",
        "",
        "Текст идеи:",
        "",
        f"«{escape_html(truncate(idea.text, 3500))}»",
        "",
        f"📊 Статус: {status_label(idea.status)}",
        f"📅 {format_datetime(idea.created_at)}",
    ]
    return "\n".join(lines)


def catalog_idea_card_text(idea, *, header: str, author: User | None = None) -> str:
    author = author or idea.author
    lines = [
        header,
        "",
        f"💡 Идея #{idea.public_number}",
        "",
        f"«{escape_html(truncate(idea.text, 700))}»",
        "",
        f"👤 Автор: {author_display(author)}",
        "",
        f"❤️ {idea.likes_count}",
        "",
        f"👁 {idea.views_count}",
        "",
        f"📅 {format_date(idea.created_at)}",
    ]
    return "\n".join(lines)
