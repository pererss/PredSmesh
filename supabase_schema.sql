-- ============================================================================
-- PredSmesh / Ideas Bot - Supabase PostgreSQL schema
-- ----------------------------------------------------------------------------
-- HOW TO USE:
--   1. Open Supabase project
--   2. SQL Editor -> New query
--   3. Paste this whole file
--   4. Press Run
--
-- The script is idempotent: it can be executed several times safely.
-- It creates the same structure as `alembic upgrade head`.
-- Use EITHER this file OR alembic, not both (see README).
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. ENUM types
-- ---------------------------------------------------------------------------
DO $$
BEGIN
    CREATE TYPE idea_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'REWARDED', 'HIDDEN');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE reward_status AS ENUM ('PENDING', 'COMPLETED', 'FAILED', 'MANUAL');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

DO $$
BEGIN
    CREATE TYPE reward_currency AS ENUM ('XTR');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ---------------------------------------------------------------------------
-- 2. Sequence for human readable idea numbers (#1, #2, #3, ...)
-- ---------------------------------------------------------------------------
CREATE SEQUENCE IF NOT EXISTS ideas_public_number_seq START WITH 1 INCREMENT BY 1;

-- ---------------------------------------------------------------------------
-- 3. users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            BIGSERIAL    NOT NULL,
    telegram_id   BIGINT       NOT NULL,
    username      VARCHAR(64),
    first_name    VARCHAR(128),
    last_name     VARCHAR(128),
    is_active     BOOLEAN      NOT NULL DEFAULT TRUE,
    is_admin      BOOLEAN      NOT NULL DEFAULT FALSE,
    referrer_id   BIGINT,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_activity TIMESTAMPTZ,
    CONSTRAINT pk_users PRIMARY KEY (id),
    CONSTRAINT fk_users_referrer_id_users FOREIGN KEY (referrer_id)
        REFERENCES users (id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_telegram_id ON users (telegram_id);
CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at);
CREATE INDEX IF NOT EXISTS ix_users_last_activity ON users (last_activity);

-- ---------------------------------------------------------------------------
-- 4. ideas
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ideas (
    id               BIGSERIAL   NOT NULL,
    public_number    INTEGER     NOT NULL,
    user_id          BIGINT      NOT NULL,
    text             TEXT        NOT NULL,
    status           idea_status NOT NULL DEFAULT 'PENDING',
    views_count      INTEGER     NOT NULL DEFAULT 0,
    likes_count      INTEGER     NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at      TIMESTAMPTZ,
    rewarded_at      TIMESTAMPTZ,
    rejection_reason TEXT,
    CONSTRAINT pk_ideas PRIMARY KEY (id),
    CONSTRAINT fk_ideas_user_id_users FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT ck_ideas_views_count_non_negative CHECK (views_count >= 0),
    CONSTRAINT ck_ideas_likes_count_non_negative CHECK (likes_count >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_ideas_public_number ON ideas (public_number);
CREATE INDEX IF NOT EXISTS ix_ideas_status ON ideas (status);
CREATE INDEX IF NOT EXISTS ix_ideas_user_id ON ideas (user_id);
CREATE INDEX IF NOT EXISTS ix_ideas_created_at ON ideas (created_at);
CREATE INDEX IF NOT EXISTS ix_ideas_likes_count ON ideas (likes_count);

-- ---------------------------------------------------------------------------
-- 5. categories
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS categories (
    id         BIGSERIAL   NOT NULL,
    name       VARCHAR(64) NOT NULL,
    slug       VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_categories PRIMARY KEY (id),
    CONSTRAINT uq_categories_name UNIQUE (name),
    CONSTRAINT uq_categories_slug UNIQUE (slug)
);

-- ---------------------------------------------------------------------------
-- 6. idea_categories (many-to-many)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idea_categories (
    idea_id     BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    CONSTRAINT pk_idea_categories PRIMARY KEY (idea_id, category_id),
    CONSTRAINT uq_idea_categories_idea_category UNIQUE (idea_id, category_id),
    CONSTRAINT fk_idea_categories_idea_id_ideas FOREIGN KEY (idea_id)
        REFERENCES ideas (id) ON DELETE CASCADE,
    CONSTRAINT fk_idea_categories_category_id_categories FOREIGN KEY (category_id)
        REFERENCES categories (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_idea_categories_category_id
    ON idea_categories (category_id);

-- ---------------------------------------------------------------------------
-- 7. likes
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS likes (
    id         BIGSERIAL   NOT NULL,
    idea_id    BIGINT      NOT NULL,
    user_id    BIGINT      NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_likes PRIMARY KEY (id),
    CONSTRAINT uq_likes_idea_user UNIQUE (idea_id, user_id),
    CONSTRAINT fk_likes_idea_id_ideas FOREIGN KEY (idea_id)
        REFERENCES ideas (id) ON DELETE CASCADE,
    CONSTRAINT fk_likes_user_id_users FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_likes_idea_id ON likes (idea_id);
CREATE INDEX IF NOT EXISTS ix_likes_user_id ON likes (user_id);

-- ---------------------------------------------------------------------------
-- 8. referrals
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS referrals (
    id          BIGSERIAL   NOT NULL,
    referrer_id BIGINT      NOT NULL,
    referred_id BIGINT      NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_referrals PRIMARY KEY (id),
    CONSTRAINT uq_referrals_referred_id UNIQUE (referred_id),
    CONSTRAINT ck_referrals_no_self_referral CHECK (referrer_id <> referred_id),
    CONSTRAINT fk_referrals_referrer_id_users FOREIGN KEY (referrer_id)
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_referrals_referred_id_users FOREIGN KEY (referred_id)
        REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_referrals_referrer_id ON referrals (referrer_id);

-- ---------------------------------------------------------------------------
-- 9. rewards
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rewards (
    id                      BIGSERIAL       NOT NULL,
    idea_id                 BIGINT          NOT NULL,
    user_id                 BIGINT          NOT NULL,
    admin_id                BIGINT,
    amount                  INTEGER         NOT NULL DEFAULT 15,
    currency                reward_currency NOT NULL DEFAULT 'XTR',
    telegram_transaction_id VARCHAR(64),
    status                  reward_status   NOT NULL DEFAULT 'PENDING',
    created_at              TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CONSTRAINT pk_rewards PRIMARY KEY (id),
    CONSTRAINT ck_rewards_amount_positive CHECK (amount > 0),
    CONSTRAINT fk_rewards_idea_id_ideas FOREIGN KEY (idea_id)
        REFERENCES ideas (id) ON DELETE CASCADE,
    CONSTRAINT fk_rewards_user_id_users FOREIGN KEY (user_id)
        REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT fk_rewards_admin_id_users FOREIGN KEY (admin_id)
        REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_rewards_idea_id ON rewards (idea_id);
CREATE INDEX IF NOT EXISTS ix_rewards_user_id ON rewards (user_id);
CREATE INDEX IF NOT EXISTS ix_rewards_status ON rewards (status);
CREATE INDEX IF NOT EXISTS ix_rewards_created_at ON rewards (created_at);

-- Only one completed/manual reward per idea (duplicate payout protection)
CREATE UNIQUE INDEX IF NOT EXISTS uq_rewards_idea_active
    ON rewards (idea_id)
    WHERE status IN ('COMPLETED', 'MANUAL');

-- ---------------------------------------------------------------------------
-- 10. admin_actions
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_actions (
    id             BIGSERIAL   NOT NULL,
    admin_id       BIGINT,
    action         VARCHAR(64) NOT NULL,
    idea_id        BIGINT,
    target_user_id BIGINT,
    details        TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_admin_actions PRIMARY KEY (id),
    CONSTRAINT fk_admin_actions_admin_id_users FOREIGN KEY (admin_id)
        REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT fk_admin_actions_idea_id_ideas FOREIGN KEY (idea_id)
        REFERENCES ideas (id) ON DELETE SET NULL,
    CONSTRAINT fk_admin_actions_target_user_id_users FOREIGN KEY (target_user_id)
        REFERENCES users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_admin_actions_created_at
    ON admin_actions (created_at);
CREATE INDEX IF NOT EXISTS ix_admin_actions_admin_id
    ON admin_actions (admin_id);

-- ---------------------------------------------------------------------------
-- 11. settings
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS settings (
    id    BIGSERIAL   NOT NULL,
    key   VARCHAR(64) NOT NULL,
    value TEXT        NOT NULL,
    CONSTRAINT pk_settings PRIMARY KEY (id),
    CONSTRAINT uq_settings_key UNIQUE (key)
);

-- ---------------------------------------------------------------------------
-- 12. Functions and triggers (auto update updated_at)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at ON users;
CREATE TRIGGER trg_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_ideas_updated_at ON ideas;
CREATE TRIGGER trg_ideas_updated_at
BEFORE UPDATE ON ideas
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ---------------------------------------------------------------------------
-- 13. Initial settings
-- ---------------------------------------------------------------------------
INSERT INTO settings (key, value) VALUES
    ('reward_amount', '15'),
    ('submissions_enabled', 'true'),
    ('notifications_enabled', 'true'),
    ('reward_gift_id', '')
ON CONFLICT (key) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 14. Initial categories
-- ---------------------------------------------------------------------------
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

-- ============================================================================
-- Done. Tables: users, ideas, categories, idea_categories, likes, referrals,
-- rewards, admin_actions, settings.
-- ============================================================================
