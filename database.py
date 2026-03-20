import logging
from datetime import datetime, timedelta
from typing import Optional, List

import asyncpg

from config import DATABASE_URL

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None

    async def init(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        await self.create_tables()

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT UNIQUE NOT NULL,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Safe migration for already created users table.
            await conn.execute(
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS last_name VARCHAR(255)
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS payments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    payment_id_yookassa VARCHAR(255) UNIQUE NOT NULL,
                    amount NUMERIC(10, 2) NOT NULL,
                    currency VARCHAR(10) DEFAULT 'RUB',
                    status VARCHAR(50) DEFAULT 'pending',
                    notified_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Safe migration for already created tables.
            await conn.execute(
                """
                ALTER TABLE payments
                ADD COLUMN IF NOT EXISTS notified_at TIMESTAMP
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    payment_id INTEGER NOT NULL REFERENCES payments(id),
                    status VARCHAR(50) DEFAULT 'active',
                    start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_date TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_payments_external_id ON payments(payment_id_yookassa)
                """
            )
            await conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uniq_active_subscription_per_user
                ON subscriptions(user_id) WHERE status = 'active'
                """
            )

    async def add_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> Optional[int]:
        async with self.pool.acquire() as conn:
            try:
                return await conn.fetchval(
                    """
                    INSERT INTO users (telegram_id, username, first_name, last_name)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (telegram_id) DO UPDATE
                    SET username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                    """,
                    telegram_id,
                    username,
                    first_name,
                    last_name,
                )
            except Exception as e:
                logger.error("Error adding user: %s", e)
                return None

    async def get_user_by_telegram_id(self, telegram_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE telegram_id = $1", telegram_id)

    async def get_user_by_id(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)

    async def create_payment(self, user_id: int, external_payment_id: str, amount: float, currency: str = "RUB") -> int:
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                INSERT INTO payments (user_id, payment_id_yookassa, amount, currency, status)
                VALUES ($1, $2, $3, $4, 'pending')
                RETURNING id
                """,
                user_id,
                external_payment_id,
                amount,
                currency,
            )

    async def get_payment_by_external_id(self, external_payment_id: str):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                "SELECT * FROM payments WHERE payment_id_yookassa = $1", external_payment_id
            )

    async def get_latest_pending_payment_by_user(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT *
                FROM payments
                WHERE user_id = $1
                  AND status IN ('pending', 'waiting_for_capture')
                ORDER BY created_at DESC
                LIMIT 1
                """,
                user_id,
            )

    async def get_pending_payments(self, limit: int = 200) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT *
                FROM payments
                WHERE status IN ('pending', 'waiting_for_capture')
                ORDER BY created_at ASC
                LIMIT $1
                """,
                limit,
            )

    async def get_latest_unnotified_succeeded_payment_by_user(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT *
                FROM payments
                WHERE user_id = $1
                  AND status = 'succeeded'
                  AND notified_at IS NULL
                ORDER BY updated_at DESC, created_at DESC
                LIMIT 1
                """,
                user_id,
            )

    async def update_payment_status(self, external_payment_id: str, status: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE payments
                SET status = $1, updated_at = CURRENT_TIMESTAMP
                WHERE payment_id_yookassa = $2
                """,
                status,
                external_payment_id,
            )

    async def mark_payment_notified(self, external_payment_id: str):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE payments
                SET notified_at = COALESCE(notified_at, CURRENT_TIMESTAMP),
                    updated_at = CURRENT_TIMESTAMP
                WHERE payment_id_yookassa = $1
                """,
                external_payment_id,
            )

    async def mark_all_unnotified_succeeded_by_user(self, user_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE payments
                SET notified_at = COALESCE(notified_at, CURRENT_TIMESTAMP),
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = $1
                  AND status = 'succeeded'
                  AND notified_at IS NULL
                """,
                user_id,
            )

    async def get_active_subscription(self, user_id: int):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT * FROM subscriptions
                WHERE user_id = $1 AND status = 'active' AND end_date > CURRENT_TIMESTAMP
                ORDER BY end_date DESC
                LIMIT 1
                """,
                user_id,
            )

    async def activate_subscription_from_payment(self, user_id: int, payment_id: int, days: int) -> datetime:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                current = await conn.fetchrow(
                    """
                    SELECT * FROM subscriptions
                    WHERE user_id = $1 AND status = 'active'
                    ORDER BY end_date DESC
                    LIMIT 1
                    FOR UPDATE
                    """,
                    user_id,
                )

                if current and current["end_date"] > datetime.utcnow():
                    new_end = current["end_date"] + timedelta(days=days)
                    await conn.execute(
                        "UPDATE subscriptions SET end_date = $1 WHERE id = $2",
                        new_end,
                        current["id"],
                    )
                    return new_end

                await conn.execute(
                    """
                    UPDATE subscriptions
                    SET status = 'expired'
                    WHERE user_id = $1 AND status = 'active'
                    """,
                    user_id,
                )

                start_date = datetime.utcnow()
                end_date = start_date + timedelta(days=days)

                await conn.execute(
                    """
                    INSERT INTO subscriptions (user_id, payment_id, status, start_date, end_date)
                    VALUES ($1, $2, 'active', $3, $4)
                    """,
                    user_id,
                    payment_id,
                    start_date,
                    end_date,
                )
                return end_date

    async def extend_subscription(self, user_id: int, days: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE subscriptions
                SET end_date = end_date + ($2::int * INTERVAL '1 day')
                WHERE user_id = $1 AND status = 'active'
                """,
                user_id,
                days,
            )

    async def expire_subscription(self, user_id: int):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE subscriptions SET status = 'expired' WHERE user_id = $1 AND status = 'active'",
                user_id,
            )

    async def get_expiring_subscriptions(self, days: int = 3) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT s.*, u.telegram_id
                FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE s.status = 'active'
                  AND s.end_date > CURRENT_TIMESTAMP
                  AND s.end_date <= CURRENT_TIMESTAMP + ($1::int * INTERVAL '1 day')
                """,
                days,
            )

    async def get_expired_subscriptions(self) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT s.*, u.telegram_id
                FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                WHERE s.status = 'active' AND s.end_date <= CURRENT_TIMESTAMP
                """
            )

    async def get_all_users(self) -> List[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT * FROM users ORDER BY created_at DESC")

    async def get_stats(self) -> dict:
        async with self.pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            active_subscriptions = await conn.fetchval(
                "SELECT COUNT(*) FROM subscriptions WHERE status = 'active' AND end_date > CURRENT_TIMESTAMP"
            )
            total_revenue = await conn.fetchval(
                "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE status = 'succeeded'"
            )
            return {
                "total_users": int(total_users or 0),
                "active_subscriptions": int(active_subscriptions or 0),
                "total_revenue": float(total_revenue or 0),
            }

    async def cancel_subscription(self, subscription_id: int):
        """Cancel subscription but keep access until end_date"""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE subscriptions SET status = 'canceled' WHERE id = $1",
                subscription_id,
            )


db = Database()
