-- SQL Примеры и запросы для управления ботом

-- ============================================
-- ПОЛЬЗОВАТЕЛИ
-- ============================================

-- Получить информацию о пользователе
SELECT * FROM users WHERE telegram_id = 123456789;

-- Получить всех пользователей
SELECT id, telegram_id, username, first_name, created_at 
FROM users 
ORDER BY created_at DESC;

-- Количество пользователей
SELECT COUNT(*) as total_users FROM users;

-- Пользователи, зарегистрировавшиеся за последние 7 дней
SELECT * FROM users 
WHERE created_at >= NOW() - INTERVAL '7 days' 
ORDER BY created_at DESC;

-- ============================================
-- ПЛАТЕЖИ
-- ============================================

-- Все платежи пользователя
SELECT p.*, u.telegram_id, u.username 
FROM payments p 
JOIN users u ON p.user_id = u.id 
WHERE u.telegram_id = 123456789 
ORDER BY p.created_at DESC;

-- Все успешные платежи
SELECT p.*, u.telegram_id 
FROM payments p 
JOIN users u ON p.user_id = u.id 
WHERE p.status = 'succeeded' 
ORDER BY p.created_at DESC;

-- Ожидающих платежи
SELECT p.*, u.telegram_id 
FROM payments p 
JOIN users u ON p.user_id = u.id 
WHERE p.status = 'pending' 
ORDER BY p.created_at DESC;

-- Неудачные платежи
SELECT p.*, u.telegram_id 
FROM payments p 
JOIN users u ON p.user_id = u.id 
WHERE p.status = 'failed' OR p.status = 'canceled' 
ORDER BY p.created_at DESC;

-- Общий доход
SELECT SUM(amount) as total_revenue 
FROM payments 
WHERE status = 'succeeded';

-- Доход за период
SELECT 
    DATE(created_at) as date,
    COUNT(*) as count,
    SUM(amount) as daily_revenue 
FROM payments 
WHERE status = 'succeeded' 
    AND created_at >= NOW() - INTERVAL '30 days' 
GROUP BY DATE(created_at) 
ORDER BY date DESC;

-- Средний размер платежа
SELECT AVG(amount) as avg_payment 
FROM payments 
WHERE status = 'succeeded';

-- ============================================
-- ПОДПИСКИ
-- ============================================

-- Активные подписки
SELECT s.*, u.telegram_id, u.username 
FROM subscriptions s 
JOIN users u ON s.user_id = u.id 
WHERE s.status = 'active' AND s.end_date > NOW() 
ORDER BY s.end_date ASC;

-- Количество активных подписок
SELECT COUNT(*) as active_subscriptions 
FROM subscriptions 
WHERE status = 'active' AND end_date > NOW();

-- Подписка заканчивается через 3 дня
SELECT s.*, u.telegram_id, u.username,
    (s.end_date - NOW())::interval as days_left 
FROM subscriptions s 
JOIN users u ON s.user_id = u.id 
WHERE s.status = 'active' 
    AND s.end_date <= NOW() + INTERVAL '3 days' 
    AND s.end_date > NOW() 
ORDER BY s.end_date ASC;

-- Истёкшие подписки
SELECT s.*, u.telegram_id, u.username 
FROM subscriptions s 
JOIN users u ON s.user_id = u.id 
WHERE s.status = 'active' AND s.end_date <= NOW() 
ORDER BY s.end_date DESC;

-- Подписка пользователя
SELECT s.*, p.payment_id_yookassa, p.amount 
FROM subscriptions s 
LEFT JOIN payments p ON s.payment_id = p.id 
WHERE s.user_id = (SELECT id FROM users WHERE telegram_id = 123456789);

-- Средняя длительность подписки
SELECT 
    AVG(EXTRACT(DAY FROM (end_date - start_date))) as avg_days 
FROM subscriptions 
WHERE status = 'expired';

-- ============================================
-- СТАТИСТИКА
-- ============================================

-- Полная статистика
SELECT 
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(*) FROM subscriptions WHERE status = 'active' AND end_date > NOW()) as active_subscriptions,
    (SELECT SUM(amount) FROM payments WHERE status = 'succeeded') as total_revenue,
    (SELECT COUNT(*) FROM payments WHERE status = 'succeeded') as successful_payments,
    (SELECT COUNT(*) FROM payments WHERE status = 'pending') as pending_payments,
    (SELECT COUNT(*) FROM payments WHERE status = 'failed' OR status = 'canceled') as failed_payments;

-- Активные пользователи (с активной подпиской)
SELECT COUNT(DISTINCT s.user_id) as active_users 
FROM subscriptions s 
WHERE s.status = 'active' AND s.end_date > NOW();

-- LTV (Lifetime Value) - средний доход от пользователя
SELECT 
    AVG(total_spent) as average_lifetime_value 
FROM (
    SELECT 
        u.id,
        SUM(p.amount) as total_spent 
    FROM users u 
    LEFT JOIN payments p ON u.id = p.user_id AND p.status = 'succeeded' 
    GROUP BY u.id
) as user_spending;

-- Retention rate (какой процент пользователей продлевают подписку)
SELECT 
    (COUNT(DISTINCT CASE WHEN repeat_users.total > 1 THEN repeat_users.user_id END)::float 
    / COUNT(DISTINCT user_id) * 100)::numeric(5,2) as retention_rate 
FROM (
    SELECT 
        user_id,
        COUNT(*) as total 
    FROM subscriptions 
    GROUP BY user_id
) as repeat_users;

-- ============================================
-- АДМИНИСТРИРОВАНИЕ
-- ============================================

-- Удалить пользователя и все его данные
DELETE FROM users WHERE telegram_id = 123456789;

-- Изменить статус подписки на expired
UPDATE subscriptions 
SET status = 'expired' 
WHERE user_id = 1 AND status = 'active';

-- Продлить подписку на 30 дней
UPDATE subscriptions 
SET end_date = end_date + INTERVAL '30 days' 
WHERE user_id = 1 AND status = 'active';

-- Отметить платёж как успешный (если он не был отмечен)
UPDATE payments 
SET status = 'succeeded' 
WHERE id = 1 AND status = 'pending';

-- Очистить данные
-- ВНИМАНИЕ: Это удалит все данные!
-- DELETE FROM subscriptions;
-- DELETE FROM payments;
-- DELETE FROM users;

-- ============================================
-- ДИАГНОСТИКА
-- ============================================

-- Проверить целостность данных
SELECT 
    'Платежи без пользователя' as issue,
    COUNT(*) as count 
FROM payments 
WHERE user_id NOT IN (SELECT id FROM users);

-- Подписки без платежей
SELECT 
    COUNT(*) as count 
FROM subscriptions 
WHERE payment_id NOT IN (SELECT id FROM payments);

-- Дублирующиеся внешние ID платежей
SELECT 
    payment_id_yookassa,
    COUNT(*) as count 
FROM payments 
GROUP BY payment_id_yookassa 
HAVING COUNT(*) > 1;

-- Активные подписки у неактивных пользователей (которые не заходили?)
-- (Требует добавления last_seen в таблицу users)
SELECT s.*, u.telegram_id 
FROM subscriptions s 
JOIN users u ON s.user_id = u.id 
WHERE s.status = 'active' 
    AND s.end_date > NOW() 
    AND u.created_at < NOW() - INTERVAL '90 days';

-- ============================================
-- ОПТИМИЗАЦИЯ
-- ============================================

-- Пересчитать индексы
REINDEX TABLE users;
REINDEX TABLE payments;
REINDEX TABLE subscriptions;

-- Анализ размера таблиц
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size 
FROM pg_tables 
WHERE schemaname NOT IN ('pg_catalog', 'information_schema') 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Статистика запросов к индексам
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched 
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
