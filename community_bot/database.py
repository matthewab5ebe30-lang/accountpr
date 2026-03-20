from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

import aiosqlite


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def initialize(self, default_price_stars: int) -> None:
        await self.connect()
        assert self._db is not None

        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                referrer_id INTEGER,
                joined_date TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS referrals (
                user_id INTEGER PRIMARY KEY,
                invited_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                chat TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

        await self._db.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            ("price_stars", str(default_price_stars)),
        )
        await self._db.commit()

    async def user_exists(self, telegram_id: int) -> bool:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT 1 FROM users WHERE telegram_id = ? LIMIT 1",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return row is not None

    async def add_user(self, telegram_id: int, referrer_id: Optional[int] = None) -> bool:
        assert self._db is not None

        if await self.user_exists(telegram_id):
            return False

        joined_date = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "INSERT INTO users (telegram_id, referrer_id, joined_date) VALUES (?, ?, ?)",
            (telegram_id, referrer_id, joined_date),
        )
        await self._db.execute(
            "INSERT OR IGNORE INTO referrals (user_id, invited_count) VALUES (?, 0)",
            (telegram_id,),
        )

        if referrer_id and referrer_id != telegram_id and await self.user_exists(referrer_id):
            await self._db.execute(
                "INSERT OR IGNORE INTO referrals (user_id, invited_count) VALUES (?, 0)",
                (referrer_id,),
            )
            await self._db.execute(
                "UPDATE referrals SET invited_count = invited_count + 1 WHERE user_id = ?",
                (referrer_id,),
            )

        await self._db.commit()
        return True

    async def get_user_joined_date(self, telegram_id: int) -> Optional[str]:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT joined_date FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return row["joined_date"] if row else None

    async def get_total_users(self) -> int:
        assert self._db is not None
        cursor = await self._db.execute("SELECT COUNT(*) AS total FROM users")
        row = await cursor.fetchone()
        return int(row["total"]) if row else 0

    async def get_quick_user_stats(self) -> tuple[int, int, int]:
        """Возвращает (всего, за 24 часа, за сегодня UTC)."""
        assert self._db is not None

        cursor = await self._db.execute("SELECT joined_date FROM users")
        rows = await cursor.fetchall()

        now = datetime.now(timezone.utc)
        day_ago = now - timedelta(hours=24)
        start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        total = len(rows)
        joined_24h = 0
        joined_today = 0

        for row in rows:
            raw_joined = row["joined_date"]
            if not raw_joined:
                continue
            try:
                joined_date = datetime.fromisoformat(raw_joined)
            except ValueError:
                continue

            if joined_date.tzinfo is None:
                joined_date = joined_date.replace(tzinfo=timezone.utc)

            if joined_date >= day_ago:
                joined_24h += 1
            if joined_date >= start_today:
                joined_today += 1

        return total, joined_24h, joined_today

    async def get_all_user_ids(self) -> List[int]:
        assert self._db is not None
        cursor = await self._db.execute("SELECT telegram_id FROM users")
        rows = await cursor.fetchall()
        return [int(row["telegram_id"]) for row in rows]

    async def get_referral_count(self, user_id: int) -> int:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT invited_count FROM referrals WHERE user_id = ?",
            (user_id,),
        )
        row = await cursor.fetchone()
        return int(row["invited_count"]) if row else 0

    async def get_top_referrers(self, limit: int = 10) -> List[Tuple[int, int]]:
        assert self._db is not None
        cursor = await self._db.execute(
            """
            SELECT user_id, invited_count
            FROM referrals
            ORDER BY invited_count DESC, user_id ASC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [(int(row["user_id"]), int(row["invited_count"])) for row in rows if row["invited_count"] > 0]

    async def save_payment(self, user_id: int, amount: int, chat: str) -> None:
        assert self._db is not None
        timestamp = datetime.now(timezone.utc).isoformat()
        await self._db.execute(
            "INSERT INTO payments (user_id, amount, chat, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, amount, chat, timestamp),
        )
        await self._db.commit()

    async def get_price_stars(self, fallback: int) -> int:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT value FROM settings WHERE key = 'price_stars'",
        )
        row = await cursor.fetchone()
        if not row:
            return fallback
        try:
            return max(1, int(row["value"]))
        except (ValueError, TypeError):
            return fallback

    async def set_price_stars(self, value: int) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO settings (key, value) VALUES ('price_stars', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(max(1, value)),),
        )
        await self._db.commit()
