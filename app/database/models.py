from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy import (
    text as sa_text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utcnow


class IdeaStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REWARDED = "REWARDED"
    HIDDEN = "HIDDEN"


class RewardStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    MANUAL = "MANUAL"


class RewardCurrency(str, enum.Enum):
    XTR = "XTR"


def _enum_values(enum_class: type[enum.Enum]) -> list[str]:
    return [item.value for item in enum_class]


IDEA_STATUS_ENUM = SAEnum(
    IdeaStatus,
    name="idea_status",
    values_callable=_enum_values,
    validate_strings=True,
)
REWARD_STATUS_ENUM = SAEnum(
    RewardStatus,
    name="reward_status",
    values_callable=_enum_values,
    validate_strings=True,
)
REWARD_CURRENCY_ENUM = SAEnum(
    RewardCurrency,
    name="reward_currency",
    values_callable=_enum_values,
    validate_strings=True,
)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id", unique=True),
        Index("ix_users_created_at", "created_at"),
        Index("ix_users_last_activity", "last_activity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=sa_text("true")
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=sa_text("false")
    )
    referrer_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_users_referrer_id_users"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Idea(Base):
    __tablename__ = "ideas"
    __table_args__ = (
        CheckConstraint("views_count >= 0", name="views_count_non_negative"),
        CheckConstraint("likes_count >= 0", name="likes_count_non_negative"),
        Index("ix_ideas_public_number", "public_number", unique=True),
        Index("ix_ideas_status", "status"),
        Index("ix_ideas_user_id", "user_id"),
        Index("ix_ideas_created_at", "created_at"),
        Index("ix_ideas_likes_count", "likes_count"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_number: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_ideas_user_id_users"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IdeaStatus] = mapped_column(
        IDEA_STATUS_ENUM,
        nullable=False,
        default=IdeaStatus.PENDING,
        server_default=sa_text("'PENDING'"),
    )
    views_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa_text("0")
    )
    likes_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa_text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rewarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    author: Mapped[User] = relationship("User", lazy="selectin")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class IdeaCategory(Base):
    __tablename__ = "idea_categories"
    __table_args__ = (
        UniqueConstraint(
            "idea_id", "category_id", name="uq_idea_categories_idea_category"
        ),
        Index("ix_idea_categories_category_id", "category_id"),
    )

    idea_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ideas.id", ondelete="CASCADE", name="fk_idea_categories_idea_id_ideas"),
        primary_key=True,
    )
    category_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "categories.id",
            ondelete="CASCADE",
            name="fk_idea_categories_category_id_categories",
        ),
        primary_key=True,
    )


class Like(Base):
    __tablename__ = "likes"
    __table_args__ = (
        UniqueConstraint("idea_id", "user_id", name="uq_likes_idea_user"),
        Index("ix_likes_idea_id", "idea_id"),
        Index("ix_likes_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    idea_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ideas.id", ondelete="CASCADE", name="fk_likes_idea_id_ideas"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_likes_user_id_users"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint("referred_id", name="uq_referrals_referred_id"),
        CheckConstraint("referrer_id <> referred_id", name="no_self_referral"),
        Index("ix_referrals_referrer_id", "referrer_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_referrals_referrer_id_users"),
        nullable=False,
    )
    referred_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_referrals_referred_id_users"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    referrer: Mapped[User] = relationship(
        "User", foreign_keys="Referral.referrer_id", lazy="selectin"
    )
    referred: Mapped[User] = relationship(
        "User", foreign_keys="Referral.referred_id", lazy="selectin"
    )


class Reward(Base):
    __tablename__ = "rewards"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_rewards_idea_id", "idea_id"),
        Index("ix_rewards_user_id", "user_id"),
        Index("ix_rewards_status", "status"),
        Index("ix_rewards_created_at", "created_at"),
        Index(
            "uq_rewards_idea_active",
            "idea_id",
            unique=True,
            postgresql_where=sa_text("status IN ('COMPLETED', 'MANUAL')"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    idea_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ideas.id", ondelete="CASCADE", name="fk_rewards_idea_id_ideas"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE", name="fk_rewards_user_id_users"),
        nullable=False,
    )
    admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_rewards_admin_id_users"),
    )
    amount: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15, server_default=sa_text("15")
    )
    currency: Mapped[RewardCurrency] = mapped_column(
        REWARD_CURRENCY_ENUM,
        nullable=False,
        default=RewardCurrency.XTR,
        server_default=sa_text("'XTR'"),
    )
    telegram_transaction_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[RewardStatus] = mapped_column(
        REWARD_STATUS_ENUM,
        nullable=False,
        default=RewardStatus.PENDING,
        server_default=sa_text("'PENDING'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )

    idea: Mapped[Idea] = relationship("Idea", lazy="selectin")
    user: Mapped[User] = relationship(
        "User", foreign_keys="Reward.user_id", lazy="selectin"
    )
    admin: Mapped[User | None] = relationship(
        "User", foreign_keys="Reward.admin_id", lazy="selectin"
    )


class AdminAction(Base):
    __tablename__ = "admin_actions"
    __table_args__ = (
        Index("ix_admin_actions_created_at", "created_at"),
        Index("ix_admin_actions_admin_id", "admin_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    admin_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_admin_actions_admin_id_users"),
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    idea_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("ideas.id", ondelete="SET NULL", name="fk_admin_actions_idea_id_ideas"),
    )
    target_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.id", ondelete="SET NULL", name="fk_admin_actions_target_user_id_users"
        ),
    )
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now()
    )


class Setting(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
