# 💡 PredSmesh — Telegram-бот для сбора и публикации идей интернет-проектов

«Придумай. Предложи. Запусти.»

Пользователи предлагают идеи стартапов, ботов, сайтов и сервисов. Администратор рассматривает
предложения, одобряет/отклоняет/скрывает их, публикует в каталоге и при необходимости награждает
авторов (15 ⭐ Telegram Stars по умолчанию).

Стек: **Python 3.11+ · aiogram 3 · SQLAlchemy 2 (async) · asyncpg · Alembic · PostgreSQL (Supabase)**.

---

## Содержание

1. [Возможности](#возможности)
2. [Структура проекта](#структура-проекта)
3. [Быстрый старт](#быстрый-старт)
4. [Переменные окружения](#переменные-окружения)
5. [Supabase: создание базы и таблиц (пошагово)](#supabase-создание-базы-и-таблиц-пошагово)
6. [Как получить пароль БД и собрать DATABASE_URL / DIRECT_URL](#как-получить-пароль-бд-и-собрать-database_url--direct_url)
7. [Alembic (альтернатива SQL-файлу)](#alembic-альтернатива-sql-файлу)
8. [Запуск локально](#запуск-локально)
9. [Docker](#docker)
10. [Деплой на Railway](#деплой-на-railway)
11. [Награды Telegram Stars: как это работает и почему есть MANUAL](#награды-telegram-stars-как-это-работает-и-почему-есть-manual)
12. [Админ-панель](#админ-панель)
13. [Безопасность](#безопасность)
14. [Частые проблемы](#частые-проблемы)

---

## Возможности

Пользователь:

- 💡 предложить идею (FSM, валидация 20–5000 символов);
- 🔎 посмотреть каталог идей (новые / популярные / случайная, пагинация, лайки, просмотры);
- 🏆 посмотреть идеи с наибольшим количеством лайков;
- ❓ узнать, как всё работает;
- 👤 посмотреть свои предложения со статусами;
- 🎁 пригласить друзей по реферальной ссылке.

Администратор (только Telegram ID `5434264152`):

- 📥 очередь новых предложений (одобрить / наградить / отклонить с причиной / написать автору / скрыть / следующее);
- 💡 все идеи и 🏆 лучшие идеи;
- 👥 пользователи со статистикой;
- ⭐ награды (pending / manual / completed / failed), ручное подтверждение выплаты;
- 📊 статистика за всё время и за сегодня;
- 📢 рассылка с предпросмотром, обработкой `TelegramRetryAfter` и деактивацией заблокировавших бота;
- ⚙️ настройки: `reward_amount`, `submissions_enabled`, `notifications_enabled`, `reward_gift_id`;
- 🏷 назначение категорий идеям вручную.

---

## Структура проекта

```
app/
    __init__.py
    bot.py                  # точка входа: python -m app.bot
    config.py               # pydantic-settings, загрузка .env
    logging_config.py       # логирование + маскировка секретов
    database/
        base.py             # DeclarativeBase, naming convention, utcnow()
        session.py          # async engine, sessionmaker, middleware, sanitize URL
        models.py           # SQLAlchemy 2 модели (users, ideas, ...)
    handlers/
        start.py            # /start (в т.ч. ref_ deep links), /help, /menu, /myideas
        user.py             # /cancel, fallback-и, обработчик ошибок
        ideas.py            # FSM подачи идеи
        catalog.py          # каталог, пагинация, лайки, просмотры
        profile.py          # «Мои предложения»
        referrals.py        # реферальная ссылка
        admin.py            # /admin, панель, статистика
        admin_ideas.py      # модерация идей, категории, сообщения автору
        admin_users.py      # пользователи
        admin_rewards.py    # награды
        admin_broadcast.py  # рассылка
        admin_settings.py   # настройки
    keyboards/              # инлайн-клавиатуры + CallbackData-фабрики
    states/                 # FSM состояния
    services/               # бизнес-логика (ideas, users, referrals, rewards,
                            # statistics, notifications, settings, admin-лог)
    repositories/           # доступ к данным (users, ideas, likes, rewards)
    utils/                  # text, pagination, telegram-хелперы
alembic/                    # env.py + versions/0001_initial.py
alembic.ini
supabase_schema.sql         # ГОТОВЫЙ SQL для Supabase SQL Editor
requirements.txt
Dockerfile
.env.example
.gitignore
README.md
```

---

## Быстрый старт

### 1. Установить Python

Нужен **Python 3.11 или новее**: https://www.python.org/downloads/
При установке на Windows отметьте галочку **«Add Python to PATH»**.

Проверка:

```bash
python --version
```

### 2. Создать виртуальное окружение

```bash
python -m venv .venv
```

Активация:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (cmd): `.venv\Scripts\activate.bat`
- macOS / Linux: `source .venv/bin/activate`

### 3. Установить зависимости

```bash
python -m pip install -r requirements.txt
```

### 4. Создать `.env`

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
copy .env.example .env      # Windows
cp .env.example .env        # macOS / Linux
```

### 5. Создать таблицы в Supabase

Откройте `supabase_schema.sql` и выполните шаги из раздела
[Supabase: создание базы и таблиц](#supabase-создание-базы-и-таблиц-пошагово).

### 6. Запустить бота

```bash
python -m app.bot
```

---

## Переменные окружения

| Переменная                  | Обязательна | Описание                                                              |
| --------------------------- | ----------- | --------------------------------------------------------------------- |
| `BOT_TOKEN`                 | да          | Токен от [@BotFather](https://t.me/BotFather). В код не вшивается.    |
| `TELEGRAM_PROXY`            | нет         | Прокси для Telegram, если сеть блокирует `api.telegram.org` (см. ниже). |
| `ADMIN_ID`                  | да          | Telegram ID администратора (`5434264152`). Проверяется на сервере.    |
| `DATABASE_URL`              | да          | Supabase pooler, порт `6543`, `?pgbouncer=true` — используется ботом. |
| `DIRECT_URL`                | да          | Supabase pooler, порт `5432` — используется Alembic.                  |
| `SUPABASE_URL`              | нет         | URL проекта Supabase (справочно).                                     |
| `SUPABASE_PUBLISHABLE_KEY`  | нет         | Publishable key (справочно).                                          |
| `REWARD_AMOUNT`             | нет         | Стартовое значение награды (по умолчанию 15).                         |
| `APP_ENV`                   | нет         | `production` / `development`.                                         |
| `LOG_LEVEL`                 | нет         | `INFO`, `DEBUG`, `WARNING`, ...                                       |

`.env.example`:

```env
BOT_TOKEN=YOUR_NEW_BOT_TOKEN
TELEGRAM_PROXY=
ADMIN_ID=5434264152
SUPABASE_URL=https://rsfjsemjbwbuiyvbbvax.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_VaDR4FHHH80K0MrV1f0ghA_341IGkoA
DATABASE_URL=postgresql://postgres.rsfjsemjbwbuiyvbbvax:YOUR_DATABASE_PASSWORD@aws-1-eu-west-1.pooler.supabase.com:6543/postgres?pgbouncer=true
DIRECT_URL=postgresql://postgres.rsfjsemjbwbuiyvbbvax:YOUR_DATABASE_PASSWORD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres
REWARD_AMOUNT=15
APP_ENV=production
LOG_LEVEL=INFO
```

> ⚠️ `.env` добавлен в `.gitignore` — не коммитьте его. Токен и пароль БД хранятся только
> в `.env` (локально) и в Environment Variables (Railway).

---

## Supabase: создание базы и таблиц (пошагово)

### ШАГ 1

Открыть Supabase Project: https://supabase.com/dashboard/project/rsfjsemjbwbuiyvbbvax

### ШАГ 2

Открыть раздел: **SQL Editor** (левое меню).

### ШАГ 3

Нажать: **New query**.

### ШАГ 4

Открыть файл: `supabase_schema.sql` (из этого проекта) обычным текстовым редактором/Блокнотом.

### ШАГ 5

Нажать: **Ctrl+A** (выделить всё).

### ШАГ 6

Нажать: **Ctrl+C** (скопировать).

### ШАГ 7

Вернуться в Supabase SQL Editor.

### ШАГ 8

Нажать: **Ctrl+V** (вставить).

### ШАГ 9

Нажать: **Run**.

### ШАГ 10

Проверить, что SQL завершился без ошибок (внизу появится `Success. No rows returned`).

### ШАГ 11

Открыть **Table Editor** и проверить наличие всех таблиц:

`users`, `ideas`, `categories`, `idea_categories`, `likes`, `referrals`, `rewards`,
`admin_actions`, `settings`.

Скрипт идемпотентный — его можно запускать повторно без ошибок.

---

## Как получить пароль БД и собрать DATABASE_URL / DIRECT_URL

1. Откройте Supabase → **Project Settings** (⚙️) → **Database**.
2. Раздел **Database password** → **Reset database password** (если пароль неизвестен).
   Сохраните новый пароль — он понадобится в URL.
3. Там же, в разделе **Connection string** → вкладка **Pooler**, скопируйте строки.
4. Соберите URL (подставьте свой пароль вместо `YOUR_DATABASE_PASSWORD`):

```
DATABASE_URL=postgresql://postgres.rsfjsemjbwbuiyvbbvax:YOUR_DATABASE_PASSWORD@aws-1-eu-west-1.pooler.supabase.com:6543/postgres?pgbouncer=true
DIRECT_URL=postgresql://postgres.rsfjsemjbwbuiyvbbvax:YOUR_DATABASE_PASSWORD@aws-1-eu-west-1.pooler.supabase.com:5432/postgres
```

Важно:

- **DATABASE_URL** (порт `6543`, transaction pooling) использует само приложение.
  Бот автоматически убирает `?pgbouncer=true` и отключает prepared statements
  (`statement_cache_size=0`) — это требование pgbouncer-режима Supabase.
- **DIRECT_URL** (порт `5432`, session pooling) использует Alembic.
- Если пароль содержит спецсимволы (`@`, `#`, `%`, `?`, `:`), закодируйте их
  (например, `@` → `%40`) или задайте новый пароль из букв и цифр.

---

## Alembic (альтернатива SQL-файлу)

`supabase_schema.sql` и Alembic создают **одну и ту же структуру**. Выбирайте один способ:

**Способ A (рекомендуется новичкам):** выполнить `supabase_schema.sql` в SQL Editor (см. выше).

**Способ B:** применить миграции Alembic (использует `DIRECT_URL`):

```bash
alembic upgrade head          # создать все таблицы
alembic downgrade base        # откатить всё (удалит таблицы)
alembic current               # текущая ревизия
alembic history               # история ревизий
alembic upgrade head --sql    # посмотреть SQL без подключения к БД
```

Если вы уже выполнили `supabase_schema.sql`, а потом хотите пользоваться Alembic — не запускайте
`upgrade` (получите ошибку «уже существует»), а отметьте ревизию как применённую:

```bash
alembic stamp head
```

---

## Запуск локально

```bash
python -m app.bot
```

При запуске бот:

1. загружает `.env`;
2. проверяет обязательные переменные (понятная ошибка, если чего-то не хватает);
3. подключается к PostgreSQL (`SELECT 1`) и создаёт отсутствующие строки настроек;
4. регистрирует команды и handlers;
5. запускает long polling;
6. логирует ошибки, не показывая пользователю traceback;
7. корректно закрывает соединения при остановке.

Остановка: `Ctrl+C`.

### Если сеть блокирует Telegram (нужен прокси)

Некоторые провайдеры/фаерволы блокируют `api.telegram.org`. Проверить:

```powershell
curl.exe -4 -s -o NUL -w "telegram=%{http_code}`n" --max-time 10 https://api.telegram.org
curl.exe -4 -s -o NUL -w "github=%{http_code}`n" --max-time 10 https://api.github.com
```

Если Telegram даёт `000` (таймаут), а GitHub — `200`, значит блокируется именно Telegram.
Решения:

1. Запусти VPN/прокси и укажи его в `.env`:

```env
TELEGRAM_PROXY=http://127.0.0.1:8080
```

Поддерживаются `http://`, `https://` и `socks5://` (например, `socks5://127.0.0.1:1080` —
локальный SOCKS-порт от VPN-клиента). Учётные данные можно указать в URL:
`http://user:pass@host:port`.

2. Либо задеплой на Railway — там доступ к Telegram есть, прокси не нужен.

Логи покажут `Using Telegram proxy: http://***@host:port` — пароль в логи не попадает.

---

## Docker

```bash
docker build -t predsmesh-bot .
docker run --env-file .env predsmesh-bot
```

Dockerfile: `python:3.11-slim`, установка `requirements.txt`, запуск `python -m app.bot`.
`.env` исключён из образа через `.dockerignore` — передавайте переменные через `--env-file`
или платформу деплоя.

---

## Деплой на Railway

1. Создайте новый Railway Project: https://railway.app/new
2. Подключите GitHub repository с этим проектом
   (**Deploy from GitHub repo** → выберите репозиторий).
3. Railway сам найдёт `Dockerfile` и соберёт образ.
4. Откройте сервис → вкладка **Variables** → **Raw Editor** и добавьте переменные:

```
BOT_TOKEN=...
ADMIN_ID=5434264152
SUPABASE_URL=https://rsfjsemjbwbuiyvbbvax.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_VaDR4FHHH80K0MrV1f0ghA_341IGkoA
DATABASE_URL=postgresql://postgres.rsfjsemjbwbuiyvbbvax:ВАШ_ПАРОЛЬ@aws-1-eu-west-1.pooler.supabase.com:6543/postgres?pgbouncer=true
DIRECT_URL=postgresql://postgres.rsfjsemjbwbuiyvbbvax:ВАШ_ПАРОЛЬ@aws-1-eu-west-1.pooler.supabase.com:5432/postgres
REWARD_AMOUNT=15
APP_ENV=production
LOG_LEVEL=INFO
```

5. **Start Command**: если Railway использует Dockerfile — ничего менять не нужно
   (`CMD ["python", "-m", "app.bot"]`). Если деплой без Dockerfile, укажите:

```
python -m app.bot
```

6. Нажмите **Deploy**. В логах должно появиться `Authorized as @your_bot (id=...)`.
7. Таблицы создаются **один раз** через `supabase_schema.sql` (или `alembic upgrade head`
   локально) — приложение само схему не меняет.

Railway засыпает? Для Telegram-бота включите постоянный режим (Settings → Restart Policy →
On Failure) и не используйте sleep.

---

## Награды Telegram Stars: как это работает и почему есть MANUAL

**Честно и без фейков:** Telegram Bot API **не содержит метода**, позволяющего боту напрямую
перевести произвольное количество Stars пользователю. Именно поэтому в проекте нет имитации
оплаты.

Как работает кнопка «⭐ Наградить N ⭐»:

1. Показывается подтверждение: «Вы действительно хотите обработать награду N ⭐ …?».
2. Проверяется защита от дублей: если по идее уже есть награда в статусе `COMPLETED` или
   `MANUAL`, повторная выплата не создаётся (плюс частичный уникальный индекс
   `uq_rewards_idea_active` в БД).
3. Если в настройках задан `reward_gift_id` (ID подарка из Bot API 8.0+ `getAvailableGifts`),
   бот пытается отправить подарок методом `sendGift` — это единственный доступный ботам способ
   передать пользователю Stars-ценность. Успех → награда `COMPLETED`.
   Неудача (подарок недоступен получателю, недостаточно баланса и т.п.) → безопасный откат
   в `MANUAL`.
4. Если `reward_gift_id` пуст (по умолчанию) → награда сохраняется со статусом **`MANUAL`**,
   а администратору показывается сообщение, что выплату нужно обработать вручную.
   Пользователю **не отправляется** сообщение о том, что Stars выплачены.
5. Когда выплата реально выполнена, администратор отмечает её выполненной в разделе
   «⭐ Награды» → награда становится `COMPLETED`, идея получает статус `REWARDED`
   и `rewarded_at`, автору уходит уведомление.

Почему `sendGift` не включён по умолчанию: подарок не конвертируется получателем в Stars и
зависит от ограничений Telegram (доступность подарка, баланс бота, настройки получателя).
Безопасный `MANUAL` — корректное поведение по умолчанию.

`telegram_transaction_id` заполняется только если он реально получен от Telegram
(при `sendGift` API его не возвращает — поле остаётся `NULL`, это нормально).

---

## Админ-панель

Доступ только по Telegram ID `5434264152` (проверяется фильтром `IsAdmin` на каждом
message/callback админ-роутера; обычный пользователь физически не может вызвать админ-callback).

- `/admin` — панель.
- 📥 Новые предложения — карточка с кнопками: ✅ Одобрить, ⭐ Наградить, ❌ Отклонить
  (6 причин, включая свою), 💬 Написать автору, 🔒 Скрыть, ➡️ Следующее.
- 💡 Все идеи / 🏆 Лучшие идеи — списки с пагинацией.
- 👥 Пользователи — счётчики, карточка пользователя (идеи, награды, рефералы, активность).
- ⭐ Награды — фильтры pending/manual/completed/failed, ручное подтверждение.
- 📊 Статистика — за всё время и за сегодня.
- 📢 Рассылка — предпросмотр, отправка с задержкой, обработка `RetryAfter`, авто-деактивация
  заблокировавших бота.
- ⚙️ Настройки — `reward_amount`, `submissions_enabled`, `notifications_enabled`, `reward_gift_id`.

Все важные действия пишутся в `admin_actions` (approve, reject, hide, reward, manual_reward,
reward_completed, broadcast, settings_change, message_user, category_change).

---

## Безопасность

- `BOT_TOKEN` и пароль БД не в коде и не в Git — только `.env` / Environment Variables.
- Логи пропускаются через фильтр, который маскирует токен и пароль (`***`).
- `ADMIN_ID` берётся только из окружения сервера, не от пользователя.
- Все админ-роутеры защищены фильтром `IsAdmin` (сравнение Telegram ID).
- Callback data короткая, передаются только ID (`idea_id`, `page`, `code`), без текстов.
- Критичные операции (лайк, approve, reject, reward, referral) выполняются в транзакциях;
  уникальные индексы защищают от гонок.
- Защита от двойной выплаты: проверка в сервисе + частичный уникальный индекс.
- Защита от повторного реферала: `UNIQUE (referred_id)` + проверка `referrer_id <> referred_id`.
- Просмотры: счётчик растёт один раз на идею на пользователя за сессию (FSM user data),
  навигация и лайки счётчик не накручивают.

---

## Частые проблемы

| Симптом | Причина / решение |
| --- | --- |
| `BOT_TOKEN не задан или имеет неверный формат` | Не создан `.env` или не заполнен `BOT_TOKEN`. |
| `Database check failed` | Не выполнен `supabase_schema.sql` / `alembic upgrade head`, либо неверный пароль в `DATABASE_URL`. |
| `invalid connection option "pgbouncer"` | Появится, если вручную заменить схему на `postgresql+asyncpg://` с параметром `pgbouncer=true`. Бот сам вычищает параметр — используйте URL как в `.env.example`. |
| `Tenant or user not found` | Неверный формат пользователя pooler (`postgres.<project-ref>`) или пароль. |
| Alembic: `relation "users" already exists` | Схема уже создана через SQL. Выполните `alembic stamp head`. |
| Бот не отвечает на Railway | Проверьте логи, переменные окружения и что запуск `python -m app.bot`; long polling не требует порта. |
| `sendGift` не работает | Оставьте `reward_gift_id` пустым — награда уйдёт в `MANUAL` и будет обработана вручную. |

---

## Лицензия

Учебный starter-проект. Используйте и изменяйте свободно.
#   P r e d S m e s h  
 