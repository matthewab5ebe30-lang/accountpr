# Telegram Community Bot (aiogram)

Новый бот создан в отдельной папке и не затрагивает текущий проект.

## Что умеет бот

- Хаб сообщества по команде `/start` с inline-кнопками:
  - 📢 Main Channel
  - 💼 Jobs
  - 💘 Dating
  - 🏠 Housing
  - 💬 General Chat
  - 🤝 Referrals
  - ⭐ Paid Announcement
- Проверка подписки на главный канал через `getChatMember`
- Модерация в группах:
  - удаление сообщений неподписанных пользователей
  - ограничение частоты сообщений
  - блокировка ссылок для новых пользователей
  - blacklist слов (опционально)
- Платные объявления за Telegram Stars
  - выбор чата
  - ввод текста
  - оплата
  - публикация + попытка временного pin
- Реферальная система:
  - deep-link `https://t.me/<bot_username>?start=<user_id>`
  - учет приглашений
  - команда `/referrals` с топом
- Админ-команды:
  - `/stats`
  - `/broadcast`
  - `/setprice`
  - `/topref`

## Структура проекта

- `bot.py` — точка входа
- `config.py` — переменные окружения и настройки
- `database.py` — SQLite и работа с таблицами
- `handlers/` — роутеры команд и событий
- `services/` — подписка, антиспам, платежная логика
- `states/` — FSM-состояния для платных объявлений
- `keyboards/` — inline-клавиатуры

## База данных (SQLite)

Создаются таблицы:

- `users`
  - `id`
  - `telegram_id`
  - `referrer_id`
  - `joined_date`
- `referrals`
  - `user_id`
  - `invited_count`
- `payments`
  - `user_id`
  - `amount`
  - `chat`
  - `timestamp`

Также используется служебная таблица `settings` для хранения цены объявления.

## Установка

1. Перейдите в папку нового бота:

```bash
cd community_bot
```

2. Создайте и активируйте виртуальное окружение (рекомендуется):

```bash
python -m venv .venv
source .venv/bin/activate
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

Если хотите установить минимально вручную:

```bash
pip install aiogram
```

## Настройка

1. Скопируйте пример переменных окружения:

```bash
cp .env.example .env
```

2. Укажите:

- `BOT_TOKEN`
- `ADMIN_IDS`
- при необходимости `COMMUNITY_CHAT_IDS`
- при необходимости `DEFAULT_PRICE_STARS`
- для Stars оставьте `STARS_PROVIDER_TOKEN` пустым (стандартный сценарий)

## Запуск

```bash
python bot.py
```

## Важные замечания

- Бот должен быть админом в community-чатах, чтобы удалять сообщения и закреплять объявления.
- Бот должен иметь доступ к главному каналу для корректной проверки подписки.
- Для корректной deep-link рефералки у бота должен быть username.
