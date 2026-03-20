# Telegram бот для продажи подписки на приватный канал

Рабочий бот для продажи доступа в приватный Telegram-канал с оплатой через Robokassa.

## Возможности

- Продажа и продление подписки через Robokassa
- Автоматическая активация подписки по Result URL
- Выдача одноразовой invite-ссылки в канал
- Напоминания перед окончанием подписки
- Автоматическое закрытие доступа после истечения
- Админ-команды для статистики и рассылок
- PostgreSQL для пользователей, платежей и подписок

## Быстрый старт

```bash
pip install -r requirements.txt
cp .env.example .env
python3 main.py
```

## Обязательные переменные

```env
BOT_TOKEN=your_bot_token
ADMIN_ID=your_telegram_id
CHANNEL_ID=your_channel_id
DATABASE_URL=postgresql://user:password@localhost:5432/subscription_bot
WEBHOOK_HOST=https://your-domain.com
WEBHOOK_PATH=/notification_url
ROBOKASSA_MERCHANT_LOGIN=your_merchant_login
ROBOKASSA_PASSWORD_1=your_password_1
ROBOKASSA_PASSWORD_2=your_password_2
ROBOKASSA_IS_TEST=1
SUBSCRIPTION_PRICE=150.00
```

## URL в кабинете Robokassa

- Result URL: https://your-domain.com/notification_url
- Success URL: https://your-domain.com/payment/success
- Fail URL: https://your-domain.com/payment/fail

Result URL поддерживает GET и POST и должен быть доступен извне.

## Оферта

- Положите документ оферты в папку `public/legal/`.
- Рекомендуемое имя: `oferta.pdf`.
- Публичная ссылка для просмотра: `https://ваш-домен/oferta`.
- Также можно открыть файл напрямую, например: `https://ваш-домен/legal/oferta.pdf`.

## Деплой на deployf.com

Используйте:

- Build command: `pip install -r requirements.txt`
- Start command: `python main.py`

Переменные окружения для хостинга:

Обязательные:

- `BOT_TOKEN`
- `ADMIN_ID`
- `CHANNEL_ID`
- `DATABASE_URL`
- `WEBHOOK_HOST` (ваш публичный URL приложения на deployf.com)
- `WEBHOOK_PATH` (обычно `/notification_url`)
- `ROBOKASSA_MERCHANT_LOGIN`
- `ROBOKASSA_PASSWORD_1`
- `ROBOKASSA_PASSWORD_2`
- `SUBSCRIPTION_PRICE` (у вас `150.00`)

Рекомендуемые/опциональные:

- `PORT` (часто задается платформой автоматически)
- `WEBHOOK_PORT` (используется, если `PORT` не задан; по умолчанию `8443`)
- `ROBOKASSA_IS_TEST` (`0` для боевого режима)
- `ROBOKASSA_API_BASE` (`https://auth.robokassa.kz/Merchant/Index.aspx`)
- `ROBOKASSA_TEST_PASSWORD_1` и `ROBOKASSA_TEST_PASSWORD_2` (только если используете кнопку тестовой оплаты)

Важно:

- В кабинете Robokassa укажите URL:
	- Result URL: `WEBHOOK_HOST + WEBHOOK_PATH`
	- Success URL: `WEBHOOK_HOST/payment/success`
	- Fail URL: `WEBHOOK_HOST/payment/fail`

## База данных

Таблицы создаются автоматически при старте:

- users
- payments
- subscriptions

## Команды

- /start
- /stats
- /users
- /broadcast <text>
- /test_expired
- /test_expiring

## Структура проекта

```text
accountpr/
├── main.py
├── config.py
├── database.py
├── handlers.py
├── robokassa_handler.py
├── scheduler.py
├── webhook_app.py
├── requirements.txt
├── run.sh
├── quickstart.sh
├── .env.example
└── README.md
```

## License

MIT
