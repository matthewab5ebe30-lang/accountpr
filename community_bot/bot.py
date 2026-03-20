from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import load_config
from database import Database
from handlers import admin, moderation, paid, referrals, start
from services.anti_spam import AntiSpamService
from services.startup_checks import validate_bot_access


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть меню сообщества"),
            BotCommand(command="referrals", description="Мои приглашения и топ"),
            BotCommand(command="stats", description="[admin] Статистика"),
            BotCommand(command="quickstats", description="[admin] Быстрые входы"),
            BotCommand(command="broadcast", description="[admin] Рассылка"),
            BotCommand(command="setprice", description="[admin] Цена объявления"),
            BotCommand(command="topref", description="[admin] Топ рефералов"),
        ]
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    config = load_config()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    db = Database(config.sqlite_path)
    await db.initialize(default_price_stars=config.default_price_stars)

    anti_spam = AntiSpamService()

    # DI-контекст: эти объекты автоматически доступны в аргументах хендлеров.
    dp["db"] = db
    dp["config"] = config
    dp["anti_spam"] = anti_spam

    dp.include_router(start.router)
    dp.include_router(referrals.router)
    dp.include_router(paid.router)
    dp.include_router(admin.router)
    dp.include_router(moderation.router)

    await set_commands(bot)
    access_report = await validate_bot_access(bot, config)
    for line in access_report:
        logging.info(line)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
