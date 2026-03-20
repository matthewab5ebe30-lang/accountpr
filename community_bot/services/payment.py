from __future__ import annotations

import asyncio
from html import escape

from aiogram import Bot


def format_paid_announcement(text: str, main_channel_url: str) -> str:
    clean_text = escape(text.strip())
    return (
        "⭐ <b>ПЛАТНОЕ ОБЪЯВЛЕНИЕ</b> ⭐\n\n"
        f"{clean_text}\n\n"
        "✅ <b>Оплачено через Telegram Stars</b>\n"
        f"📢 Основной канал: {main_channel_url}"
    )


def schedule_unpin(bot: Bot, chat_id: str | int, message_id: int, delay_seconds: int) -> None:
    async def _worker() -> None:
        await asyncio.sleep(delay_seconds)
        try:
            await bot.unpin_chat_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            # Если не получилось открепить, это не должно ломать работу бота.
            pass

    asyncio.create_task(_worker())
