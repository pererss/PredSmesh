"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-09-20

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


idea_status = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    "REWARDED",
    "HIDDEN",
    name="idea_status",
    create_type=False,
)
reward_status = postgresql.ENUM(
    "PENDING",
    "COMPLETED",
    "FAILED",
    "MANUAL",
    name="reward_status",
    create_type=False,
)
reward_currency = postgresql.ENUM(
    "XTR",
    name="reward_currency",
    create_type=False,
)

ENUM_STATEMENTS = (
    """
DO $$
BEGIN
    CREATE TYPE idea_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'REWARDED', 'HIDDEN');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
""",
    """
DO $$
BEGIN
    CREATE TYPE reward_status AS ENUM ('PENDING', 'COMPLETED', 'FAILED', 'MANUAL');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
""",
    """
DO $$
BEGIN
    CREATE TYPE reward_currency AS ENUM ('XTR');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
""",
)

TRIGGER_STATEMENTS = (
    """
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
""",
    "DROP TRIGGER IF EXISTS trg_users_updated_at ON users;",
    """
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
""",
    "DROP TRIGGER IF EXISTS trg_ideas_updated_at ON ideas;",
    """
CREATE TRIGGER trg_ideas_updated_at
BEFORE UPDATE ON ideas
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
""",
)

SEED_STATEMENTS = (
    """
INSERT INTO settings (key, value) VALUES
    ('reward_amount', '15'),
    ('submissions_enabled', 'true'),
    ('notifications_enabled', 'true'),
    ('reward_gift_id', '')
ON CONFLICT (key) DO NOTHING;
""",
    """
INSERT INTO categories (name, slug) VALUES
    ('🤖 AI', 'ai'),
    ('📱 Приложения', 'apps'),
    ('🌐 Сайты', 'sites'),
    ('🤖 Telegram-боты', 'telegram-bots'),
    ('💼 Сервисы', 'services'),
    ('🛒 E-commerce', 'ecommerce'),
    ('🎮 Игры', 'games'),
    ('💰 Финансы', 'finance'),
    ('📣 Маркетинг', 'marketing'),
    ('🛠 Инструменты', 'tools'),
    ('📦 Другое', 'other')
ON CONFLICT DO NOTHING;
""",
)


def upgrade() -> None:
    for statement in ENUM_STATEMENTS:
        op.execute(statement)

    op.execute(
        "CREATE SEQUENCE IF NOT EXISTS ideas_public_number_seq "
        "START WITH 1 INCREMENT BY 1;"
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=128), nullable=True),
        sa.Column("last_name", sa.String(length=128), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("referrer_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.ForeignKeyConstraint(
            ["referrer_id"],
            ["users.id"],
            name="fk_users_referrer_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)
    op.create_index("ix_users_last_activity", "users", ["last_activity"], unique=False)

    op.create_table(
        "ideas",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("public_number", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", idea_status, server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column(
            "views_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "likes_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rewarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_ideas"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_ideas_user_id_users",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "views_count >= 0", name="ck_ideas_views_count_non_negative"
        ),
        sa.CheckConstraint(
            "likes_count >= 0", name="ck_ideas_likes_count_non_negative"
        ),
    )
    op.create_index("ix_ideas_public_number", "ideas", ["public_number"], unique=True)
    op.create_index("ix_ideas_status", "ideas", ["status"], unique=False)
    op.create_index("ix_ideas_user_id", "ideas", ["user_id"], unique=False)
    op.create_index("ix_ideas_created_at", "ideas", ["created_at"], unique=False)
    op.create_index("ix_ideas_likes_count", "ideas", ["likes_count"], unique=False)

    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_categories"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )

    op.create_table(
        "idea_categories",
        sa.Column("idea_id", sa.BigInteger(), nullable=False),
        sa.Column("category_id", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("idea_id", "category_id", name="pk_idea_categories"),
        sa.ForeignKeyConstraint(
            ["idea_id"],
            ["ideas.id"],
            name="fk_idea_categories_idea_id_ideas",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name="fk_idea_categories_category_id_categories",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "idea_id", "category_id", name="uq_idea_categories_idea_category"
        ),
    )
    op.create_index(
        "ix_idea_categories_category_id",
        "idea_categories",
        ["category_id"],
        unique=False,
    )

    op.create_table(
        "likes",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("idea_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_likes"),
        sa.ForeignKeyConstraint(
            ["idea_id"], ["ideas.id"], name="fk_likes_idea_id_ideas", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_likes_user_id_users", ondelete="CASCADE"
        ),
        sa.UniqueConstraint("idea_id", "user_id", name="uq_likes_idea_user"),
    )
    op.create_index("ix_likes_idea_id", "likes", ["idea_id"], unique=False)
    op.create_index("ix_likes_user_id", "likes", ["user_id"], unique=False)

    op.create_table(
        "referrals",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("referrer_id", sa.BigInteger(), nullable=False),
        sa.Column("referred_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_referrals"),
        sa.ForeignKeyConstraint(
            ["referrer_id"],
            ["users.id"],
            name="fk_referrals_referrer_id_users",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["referred_id"],
            ["users.id"],
            name="fk_referrals_referred_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("referred_id", name="uq_referrals_referred_id"),
        sa.CheckConstraint(
            "referrer_id <> referred_id", name="ck_referrals_no_self_referral"
        ),
    )
    op.create_index(
        "ix_referrals_referrer_id", "referrals", ["referrer_id"], unique=False
    )

    op.create_table(
        "rewards",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("idea_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Integer(), server_default=sa.text("15"), nullable=False),
        sa.Column(
            "currency",
            reward_currency,
            server_default=sa.text("'XTR'"),
            nullable=False,
        ),
        sa.Column("telegram_transaction_id", sa.String(length=64), nullable=True),
        sa.Column(
            "status", reward_status, server_default=sa.text("'PENDING'"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rewards"),
        sa.ForeignKeyConstraint(
            ["idea_id"],
            ["ideas.id"],
            name="fk_rewards_idea_id_ideas",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_rewards_user_id_users", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["users.id"],
            name="fk_rewards_admin_id_users",
            ondelete="SET NULL",
        ),
        sa.CheckConstraint("amount > 0", name="ck_rewards_amount_positive"),
    )
    op.create_index("ix_rewards_idea_id", "rewards", ["idea_id"], unique=False)
    op.create_index("ix_rewards_user_id", "rewards", ["user_id"], unique=False)
    op.create_index("ix_rewards_status", "rewards", ["status"], unique=False)
    op.create_index("ix_rewards_created_at", "rewards", ["created_at"], unique=False)
    op.create_index(
        "uq_rewards_idea_active",
        "rewards",
        ["idea_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('COMPLETED', 'MANUAL')"),
    )

    op.create_table(
        "admin_actions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("admin_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("idea_id", sa.BigInteger(), nullable=True),
        sa.Column("target_user_id", sa.BigInteger(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_admin_actions"),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["users.id"],
            name="fk_admin_actions_admin_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["idea_id"],
            ["ideas.id"],
            name="fk_admin_actions_idea_id_ideas",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name="fk_admin_actions_target_user_id_users",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_admin_actions_created_at", "admin_actions", ["created_at"], unique=False
    )
    op.create_index(
        "ix_admin_actions_admin_id", "admin_actions", ["admin_id"], unique=False
    )

    op.create_table(
        "settings",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_settings"),
        sa.UniqueConstraint("key", name="uq_settings_key"),
    )

    for statement in TRIGGER_STATEMENTS:
        op.execute(statement)

    for statement in SEED_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_ideas_updated_at ON ideas;")
    op.execute("DROP TRIGGER IF EXISTS trg_users_updated_at ON users;")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    op.drop_table("settings")
    op.drop_table("admin_actions")
    op.drop_table("rewards")
    op.drop_table("referrals")
    op.drop_table("likes")
    op.drop_table("idea_categories")
    op.drop_table("categories")
    op.drop_table("ideas")
    op.drop_table("users")

    op.execute("DROP SEQUENCE IF EXISTS ideas_public_number_seq;")
    op.execute("DROP TYPE IF EXISTS reward_currency;")
    op.execute("DROP TYPE IF EXISTS reward_status;")
    op.execute("DROP TYPE IF EXISTS idea_status;")
