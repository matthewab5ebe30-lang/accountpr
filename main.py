import asyncio
import logging
import sys
from datetime import datetime, timedelta
from aiogram import Dispatcher, Bot
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web

from config import (
    BOT_TOKEN, CHANNEL_ID, WEBHOOK_HOST, WEBHOOK_PORT,
    WEBHOOK_PATH
)
from database import db
from handlers import router
from scheduler import SubscriptionScheduler
from webhook_app import create_app, set_bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🔄 Перезагрузить"),
        BotCommand(command="stats", description="📊 Статистика (админ)"),
        BotCommand(command="users", description="👥 Список пользователей (админ)"),
        BotCommand(command="broadcast", description="📢 Рассылка (админ)"),
        BotCommand(command="test_expired", description="🧪 Проверить истекшие (админ)"),
        BotCommand(command="test_expiring", description="⏰ Проверить заканчивающиеся (админ)")
    ]
    await bot.set_my_commands(commands)

async def main():
    await db.init()
    logger.info("Database initialized")
    
    storage = MemoryStorage()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    
    dp.include_router(router)
    
    await set_bot_commands(bot)
    await set_bot(bot)
    
    scheduler = SubscriptionScheduler(bot)
    scheduler.start()
    logger.info("Scheduler started")
    
    web_app = create_app()
    
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', WEBHOOK_PORT)
    await site.start()
    
    logger.info(f"Webhook server started on port {WEBHOOK_PORT}")
    
    try:
        me = await bot.get_me()
        logger.info("Bot token is valid, username: @%s", me.username)
    except Exception as e:
        logger.error(f"Invalid bot token: {e}")
        await runner.cleanup()
        await bot.session.close()
        await db.close()
        return
    
    try:
        logger.info("Bot is polling for updates...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Error during polling: {e}")
    finally:
        scheduler.stop()
        await runner.cleanup()
        await bot.session.close()
        await db.close()
        logger.info("Bot shutdown completed")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
