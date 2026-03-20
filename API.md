# API Документация Telegram Бота

## Структура базы данных

### Таблица: users

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Описание:**
- `id` - уникальный идентификатор пользователя в БД
- `telegram_id` - ID пользователя в Telegram (уникален)
- `username` - имя пользователя в Telegram
- `first_name` - имя пользователя
- `created_at` - дата регистрации

**Примеры запросов:**

```sql
-- Получить пользователя по Telegram ID
SELECT * FROM users WHERE telegram_id = 123456789;

-- Получить всех пользователей
SELECT * FROM users ORDER BY created_at DESC;

-- Количество пользователей
SELECT COUNT(*) FROM users;
```

### Таблица: payments

```sql
CREATE TABLE payments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payment_id_yookassa VARCHAR(255) UNIQUE NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'RUB',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Описание:**
- `id` - уникальный идентификатор платежа в БД
- `user_id` - ID пользователя (FK)
- `payment_id_yookassa` - внешний ID платежа провайдера; историческое имя колонки сохранено для совместимости
- `amount` - сумма платежа в рублях
- `currency` - валюта (RUB)
- `status` - статус платежа (pending, succeeded, failed)
- `created_at` - дата создания платежа
- `updated_at` - дата обновления статуса

**Статусы платежей:**
- `pending` - ожидание подтверждения
- `succeeded` - успешно оплачено
- `failed` - платёж отклонен
- `canceled` - платёж отменён

**Примеры запросов:**

```sql
-- Получить все платежи пользователя
SELECT * FROM payments WHERE user_id = 1 ORDER BY created_at DESC;

-- Получить успешные платежи
SELECT * FROM payments WHERE status = 'succeeded' ORDER BY created_at DESC;

-- Сумма всех успешных платежей
SELECT SUM(amount) FROM payments WHERE status = 'succeeded';

-- Платежи за последние 7 дней
SELECT * FROM payments 
WHERE created_at >= NOW() - INTERVAL '7 days' 
ORDER BY created_at DESC;
```

### Таблица: subscriptions

```sql
CREATE TABLE subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    payment_id INTEGER NOT NULL REFERENCES payments(id),
    status VARCHAR(50) DEFAULT 'active',
    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Описание:**
- `id` - уникальный идентификатор подписки
- `user_id` - ID пользователя (FK)
- `payment_id` - ID платежа (FK)
- `status` - статус подписки (active, expired)
- `start_date` - дата начала подписки
- `end_date` - дата окончания подписки
- `created_at` - дата создания записи

**Статусы подписок:**
- `active` - активная подписка
- `expired` - истекшая подписка

**Примеры запросов:**

```sql
-- Получить активную подписку пользователя
SELECT * FROM subscriptions 
WHERE user_id = 1 AND status = 'active' AND end_date > NOW();

-- Получить все активные подписки
SELECT s.*, u.telegram_id FROM subscriptions s 
JOIN users u ON s.user_id = u.id 
WHERE s.status = 'active' AND s.end_date > NOW();

-- Подписки заканчивающиеся через 3 дня
SELECT s.*, u.telegram_id FROM subscriptions s 
JOIN users u ON s.user_id = u.id 
WHERE s.status = 'active' 
AND s.end_date <= NOW() + INTERVAL '3 days' 
AND s.end_date > NOW();

-- Истёкшие подписки
SELECT s.*, u.telegram_id FROM subscriptions s 
JOIN users u ON s.user_id = u.id 
WHERE s.status = 'active' AND s.end_date <= NOW();

-- Количество активных подписок
SELECT COUNT(*) FROM subscriptions WHERE status = 'active' AND end_date > NOW();
```

## Robokassa callback

### Result URL

- Путь: `/notification_url`
- Методы: GET и POST
- Параметры: `OutSum`, `InvId`, `SignatureValue`

### Логика обработки

1. Проверка подписи через Password #2
2. Поиск платежа по внешнему ID
3. Проверка суммы against записи в БД
4. Перевод платежа в `succeeded`
5. Активация или продление подписки на 30 дней
6. Отправка одноразовой invite-ссылки пользователю
7. Ответ Robokassa в формате `OK<InvId>`

## Логирование

Все события логируются в консоль и файл.

**Уровни логирования:**
- `INFO` - информационные сообщения
- `ERROR` - ошибки
- `WARNING` - предупреждения
- `DEBUG` - отладочная информация

**Примеры логов:**

```
2024-03-04 12:00:00 - database - INFO - Database initialized
2024-03-04 12:00:01 - handlers - INFO - User 123456789 started bot
2024-03-04 12:00:05 - robokassa_handler - INFO - Robokassa payment created inv_id=171000001 user_id=1 out_sum=100.00
2024-03-04 12:00:10 - webhook_app - INFO - Payment 254c2c3d-0b1c-4f6d-8f1f-2e3c4d5e6f7g processed successfully
2024-03-04 12:00:10 - database - INFO - Subscription 1 created for user 1
```

## Администраторские функции

### /stats

Показывает статистику:

```
📊 Статистика бота

👥 Всего пользователей: 150
✅ Активных подписок: 45
💰 Общий доход: 1350.00 ₽
```

**SQL запрос:**
```sql
SELECT 
    COUNT(DISTINCT u.id) as total_users,
    COUNT(DISTINCT CASE WHEN s.status = 'active' AND s.end_date > NOW() THEN s.id END) as active_subscriptions,
    COALESCE(SUM(p.amount), 0) as total_revenue
FROM users u
LEFT JOIN subscriptions s ON u.id = s.user_id
LEFT JOIN payments p ON s.payment_id = p.id AND p.status = 'succeeded';
```

### /users

Показывает список пользователей (максимум 50):

```
👥 Список пользователей:

John Doe (@johndoe) - 123456789
Jane Smith (@janesmith) - 987654321
...
```

### /broadcast <message>

Отправляет сообщение всем пользователям (только админу).

Пример:
```
/broadcast 🎉 Новое обновление! Подписка теперь дешевле!
```

## Обработка ошибок

### Ошибки БД

```
ERROR - database - Error adding user: relation "users" does not exist
```

**Решение:** Убедитесь, что таблицы созданы или пересоздайте их.

### Ошибки Webhook

```
ERROR - webhook_app - Webhook error: [error message]
```

**Возможные причины:**
- Неверная подпись webhook
- Платёж уже обработан
- Пользователь не найден в БД
- Сумма платежа не совпадает

### Ошибки Robokassa

```
ERROR - webhook_app - Robokassa ResultURL error: [error message]
```

**Возможные причины:**
- Неверный ROBOKASSA_PASSWORD_1 или ROBOKASSA_PASSWORD_2
- Result URL недоступен снаружи
- Сумма callback не совпадает с БД
- Платёж уже обработан ранее

## Примеры использования API базы данных

### Python - asyncpg

```python
from database import db

# Получить активную подписку пользователя
subscription = await db.get_active_subscription(user_id=1)

# Создать платёж
payment_id = await db.create_payment(
    user_id=1,
    external_payment_id="payment_123",
    amount=30.0
)

# Обновить статус платежа
await db.update_payment_status("payment_123", "succeeded")

# Получить статистику
stats = await db.get_stats()
print(f"Users: {stats['total_users']}")
print(f"Active subscriptions: {stats['active_subscriptions']}")
print(f"Revenue: {stats['total_revenue']}")
```

## Безопасность

### Защита от фрода

1. **Проверка подписи callback** - подпись Robokassa проверяется через Password #2
2. **Проверка статуса платежа** - повторная обработка `succeeded` не приводит к дублям
3. **Проверка суммы платежа** - сумма callback должна совпасть с ожидаемой
4. **Одноразовое использование платежа** - повторный callback не создаёт повторную подписку
5. **Защита от дублей** - активная подписка у пользователя поддерживается в одном экземпляре

### SSL/TLS

Все webhook обработаны по HTTPS. Используйте свой сертификат или Let's Encrypt.

### Логирование чувствительных данных

Логируются только:
- Payment ID (не полный)
- User ID
- Сумма платежа
- Статус

НЕ логируются:
- Номера карт
- CVV коды
- Секретные ключи
- Пароли
