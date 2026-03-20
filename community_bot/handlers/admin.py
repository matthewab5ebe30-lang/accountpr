from __future__ import annotations

import asyncio

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.types import Message

from config import Config
from database import Database


router = Router()


def _is_admin(user_id: int, admin_ids: list[int]) -> bool:
    return user_id in admin_ids


def _format_top_referrers(rows: list[tuple[int, int]]) -> str:
    if not rows:
        return "Пока нет данных по приглашениям."

    lines = ["<b>Топ рефереров:</b>"]
    for idx, (user_id, count) in enumerate(rows, start=1):
        lines.append(f"{idx}. <a href='tg://user?id={user_id}'>Пользователь {user_id}</a> — {count}")
    return "\n".join(lines)


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or not _is_admin(message.from_user.id, config.admin_ids):
        return

    total_users, joined_24h, joined_today = await db.get_quick_user_stats()
    price = await db.get_price_stars(config.default_price_stars)

    await message.answer(
        f"<b>Статистика:</b>\n"
        f"Всего зашло в бота: {total_users}\n"
        f"За 24 часа: {joined_24h}\n"
        f"За сегодня (UTC): {joined_today}\n"
        f"Текущая цена объявления: {price} Stars"
    )


@router.message(Command("quickstats"))
async def cmd_quickstats(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or not _is_admin(message.from_user.id, config.admin_ids):
        return

    total_users, joined_24h, joined_today = await db.get_quick_user_stats()
    await message.answer(
        f"<b>Быстрая статистика:</b>\n"
        f"Всего зашло: {total_users}\n"
        f"За 24 часа: {joined_24h}\n"
        f"За сегодня: {joined_today}"
    )


@router.message(Command("setprice"))
async def cmd_setprice(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or not _is_admin(message.from_user.id, config.admin_ids):
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Использование: /setprice 50")
        return

    new_price = max(1, int(parts[1].strip()))
    await db.set_price_stars(new_price)
    await message.answer(f"Новая цена установлена: {new_price} Stars")


@router.message(Command("topref"))
async def cmd_topref(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or not _is_admin(message.from_user.id, config.admin_ids):
        return

    leaderboard = await db.get_top_referrers(limit=10)
    await message.answer(_format_top_referrers(leaderboard))


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, db: Database, config: Config) -> None:
    if not message.from_user or not _is_admin(message.from_user.id, config.admin_ids):
        return

    user_ids = await db.get_all_user_ids()
    if not user_ids:
        await message.answer("Нет пользователей для рассылки.")
        return

    text_payload = ""
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1:
        text_payload = parts[1]

    if not text_payload and not message.reply_to_message:
        await message.answer("Использование: /broadcast текст\nИли ответьте на сообщение командой /broadcast")
        return

    success = 0
    failed = 0

    for uid in user_ids:
        try:
            if message.reply_to_message:
                await message.reply_to_message.copy_to(uid)
            else:
                await message.bot.send_message(uid, text_payload)
            success += 1
            await asyncio.sleep(0.04)
        except TelegramRetryAfter as err:
            await asyncio.sleep(float(err.retry_after) + 0.2)
            try:
                if message.reply_to_message:
                    await message.reply_to_message.copy_to(uid)
                else:
                    await message.bot.send_message(uid, text_payload)
                success += 1
            except (TelegramForbiddenError, TelegramBadRequest):
                failed += 1
        except (TelegramForbiddenError, TelegramBadRequest):
            failed += 1

    await message.answer(f"Рассылка завершена. Доставлено: {success}, ошибок: {failed}")
