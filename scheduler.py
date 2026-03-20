import logging
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from database import db
from config import REMINDER_DAYS, CHANNEL_ID, SUBSCRIPTION_DAYS

logger = logging.getLogger(__name__)

class SubscriptionScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.scheduler = AsyncIOScheduler()

    async def check_expiring_subscriptions(self):
        try:
            expiring = await db.get_expiring_subscriptions(REMINDER_DAYS)
            
            for subscription in expiring:
                telegram_id = subscription["telegram_id"]
                end_date = subscription["end_date"]
                days_left = (end_date - datetime.now()).days

                if days_left == REMINDER_DAYS:
                    await self.send_reminder(telegram_id, days_left)
                    
        except Exception as e:
            logger.error(f"Error in check_expiring_subscriptions: {e}")

    async def check_expired_subscriptions(self):
        try:
            expired = await db.get_expired_subscriptions()
            
            for subscription in expired:
                telegram_id = subscription["telegram_id"]
                user_id = subscription["user_id"]
                
                await db.expire_subscription(user_id)
                
                try:
                    try:
                        await self.bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=telegram_id)
                        await self.bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=telegram_id)
                    except Exception as remove_err:
                        logger.warning("Could not remove user %s from channel: %s", telegram_id, remove_err)

                    await self.bot.send_message(
                        chat_id=telegram_id,
                        text="❌ Ваша подписка истекла.\n\nДоступ к каналу был закрыт."
                    )
                except Exception as e:
                    logger.warning(f"Could not send expiry message to {telegram_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in check_expired_subscriptions: {e}")

    async def send_success_message(self, telegram_id: int) -> bool:
        """Send payment success message with channel and menu buttons."""
        try:
            invite_link = await self.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🟢 Перейти в канал", url=invite_link.invite_link)],
                    [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
                ]
            )
            await self.bot.send_message(
                chat_id=telegram_id,
                text="✅ Оплата прошла успешно!\n\nДобро пожаловать в канал.",
                reply_markup=keyboard,
            )
            return True
        except Exception as e:
            logger.warning("Failed to send success invite to %s: %s", telegram_id, e)
            try:
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🏠 Меню", callback_data="menu")]]
                )
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text="✅ Оплата прошла успешно! Подписка активирована. Нажмите /start.",
                    reply_markup=keyboard,
                )
                return True
            except Exception as send_error:
                logger.warning("Failed fallback success message to %s: %s", telegram_id, send_error)
                return False

    async def send_reminder(self, telegram_id: int, days_left: int):
        try:
            from handlers import get_inline_keyboard_renew
            
            keyboard = get_inline_keyboard_renew()
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=f"⏳ Ваша подписка заканчивается через {days_left} дней.\n\n"
                     f"Продлите её чтобы не потерять доступ.",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending reminder to {telegram_id}: {e}")

    def start(self):
        try:
            self.scheduler.add_job(
                self.check_expired_subscriptions,
                CronTrigger(hour=0, minute=0),
                id="check_expired",
                name="Check expired subscriptions",
                replace_existing=True
            )
            
            self.scheduler.add_job(
                self.check_expiring_subscriptions,
                CronTrigger(hour=9, minute=0),
                id="check_expiring",
                name="Check expiring subscriptions",
                replace_existing=True
            )
            self.scheduler.start()
            logger.info("Subscription scheduler started")
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Subscription scheduler stopped")
