# ПЕРВЫЙ ЗАПУСК БОТА

## Требования

- Python 3.10+
- PostgreSQL 12+
- Telegram BOT TOKEN
- Учётная запись Robokassa

## Что нужно подготовить

1. BOT_TOKEN у @BotFather
2. ADMIN_ID вашего Telegram-аккаунта
3. CHANNEL_ID приватного канала
4. ROBOKASSA_MERCHANT_LOGIN
5. ROBOKASSA_PASSWORD_1
6. ROBOKASSA_PASSWORD_2
7. Публичный домен или туннель для Result URL

## Настройка .env

```bash
cp .env.example .env
nano .env
```

Минимальный набор:

```env
BOT_TOKEN=ваш_токен
ADMIN_ID=ваш_telegram_id
CHANNEL_ID=id_канала
DATABASE_URL=postgresql://subscription_user:your_password@localhost:5432/subscription_bot
WEBHOOK_HOST=https://your-domain.com
WEBHOOK_PATH=/notification_url
ROBOKASSA_MERCHANT_LOGIN=merchant_login
ROBOKASSA_PASSWORD_1=password1
ROBOKASSA_PASSWORD_2=password2
ROBOKASSA_IS_TEST=1
SUBSCRIPTION_PRICE=150.00
```

## Установка и запуск

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 test_bot.py
python3 main.py
```

## Настройка PostgreSQL

```bash
createdb subscription_bot
createuser subscription_user
psql -U postgres
ALTER USER subscription_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE subscription_bot TO subscription_user;
```

## Настройка Robokassa

В кабинете укажите:

- Result URL: https://your-domain.com/notification_url
- Success URL: https://your-domain.com/payment/success
- Fail URL: https://your-domain.com/payment/fail

## Проверка работы

1. Откройте бота и отправьте /start
2. Нажмите Купить подписку
3. Проверьте переход на страницу Robokassa
4. Проведите тестовую оплату
5. Убедитесь, что после callback подписка активировалась и пришла ссылка в канал

## Частые проблемы

### Не подключается PostgreSQL

Запустите сервис PostgreSQL и проверьте DATABASE_URL.

### Webhook не срабатывает

Проверьте, что Result URL доступен извне и совпадает с WEBHOOK_HOST + WEBHOOK_PATH.

### Платёж создаётся, но подписка не активируется

Проверьте ROBOKASSA_PASSWORD_2 и логи webhook-обработчика.

## Автоматический запуск

```bash
bash quickstart.sh
```
- ✅ Бот работает локально
- ✅ Платежи обрабатываются
- ✅ Подписки создаются
- ✅ Уведомления отправляются

Далее для production:
- Развернуть на VPS
- Настроить SSL
- Настроить собственный домен
- Настроить мониторинг
- Настроить backup БД
