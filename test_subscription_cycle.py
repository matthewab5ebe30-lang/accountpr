#!/usr/bin/env python3
"""
Скрипт для тестирования полного цикла подписки
"""
import asyncio
import sys
from datetime import datetime, timedelta
from database import db
from config import ADMIN_ID

async def create_test_subscription():
    """Создать тестовую подписку с коротким сроком для проверки удаления"""
    print("\n🧪 === СОЗДАНИЕ ТЕСТОВОЙ ПОДПИСКИ ===\n")
    
    telegram_id = int(input("Введите ваш Telegram ID (например, 893668210): "))
    minutes = int(input("Срок подписки в минутах (например, 2): "))
    
    await db.init()
    
    # Получаем или создаем пользователя
    user = await db.get_user_by_telegram_id(telegram_id)
    if not user:
        print(f"❌ Пользователь {telegram_id} не найден в БД")
        print("💡 Отправьте /start боту, чтобы зарегистрироваться")
        await db.close()
        return
    
    # Создаем тестовый платеж
    payment_id = f"test_{telegram_id}_{int(datetime.now().timestamp())}"
    await db.create_payment(
        user_id=user["id"],
        external_payment_id=payment_id,
        amount=100.00,
        currency="RUB"
    )
    
    payment = await db.get_payment_by_external_id(payment_id)
    await db.update_payment_status(payment_id, "succeeded")
    
    # Активируем подписку с коротким сроком
    start_date = datetime.now()
    end_date = start_date + timedelta(minutes=minutes)
    
    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO subscriptions (user_id, payment_id, status, start_date, end_date)
            VALUES ($1, $2, 'active', $3, $4)
            """,
            user["id"],
            payment["id"],
            start_date,
            end_date,
        )
    
    print(f"\n✅ Тестовая подписка создана!")
    print(f"👤 Пользователь: {user['first_name']} (TG ID: {telegram_id})")
    print(f"⏰ Истекает: {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏳ Через {minutes} минут")
    print(f"\n💡 Теперь запустите: python test_subscription_cycle.py --check-expired")
    print(f"   Эта команда вручную проверит и удалит истекшие подписки\n")
    
    await db.close()


async def check_expired_now():
    """Вручную запустить проверку истекших подписок (для тестирования)"""
    print("\n🔍 === ПРОВЕРКА ИСТЕКШИХ ПОДПИСОК ===\n")
    
    await db.init()
    
    # Импортируем бота
    from main import bot, BOT_TOKEN
    from aiogram import Bot
    from config import CHANNEL_ID
    
    test_bot = Bot(token=BOT_TOKEN)
    
    try:
        # Получаем истекшие подписки
        expired = await db.get_expired_subscriptions()
        
        if not expired:
            print("✅ Нет истекших подписок")
            await db.close()
            await test_bot.session.close()
            return
        
        print(f"📋 Найдено истекших подписок: {len(expired)}\n")
        
        for subscription in expired:
            telegram_id = subscription["telegram_id"]
            user_id = subscription["user_id"]
            end_date = subscription["end_date"]
            
            print(f"⏰ Обработка: TG ID {telegram_id}")
            print(f"   Истекла: {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Меняем статус на expired
            await db.expire_subscription(user_id)
            print(f"   ✅ Статус изменен на 'expired'")
            
            # Пытаемся удалить из канала
            try:
                await test_bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=telegram_id)
                await test_bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=telegram_id)
                print(f"   ✅ Удален из канала")
            except Exception as remove_err:
                print(f"   ⚠️ Не удалось удалить из канала: {remove_err}")
            
            # Отправляем уведомление
            try:
                await test_bot.send_message(
                    chat_id=telegram_id,
                    text="❌ Ваша подписка истекла.\n\nДоступ к каналу был закрыт.\n\nВы можете купить новую подписку в любой момент."
                )
                print(f"   ✅ Уведомление отправлено")
            except Exception as msg_err:
                print(f"   ⚠️ Не удалось отправить уведомление: {msg_err}")
            
            print()
        
        print("✅ Проверка завершена!")
        
    finally:
        await db.close()
        await test_bot.session.close()


async def check_expiring_now():
    """Вручную запустить проверку заканчивающихся подписок"""
    print("\n⏰ === ПРОВЕРКА ЗАКАНЧИВАЮЩИХСЯ ПОДПИСОК ===\n")
    
    await db.init()
    
    from main import BOT_TOKEN
    from aiogram import Bot
    from handlers import get_inline_keyboard_renew
    from config import REMINDER_DAYS
    
    test_bot = Bot(token=BOT_TOKEN)
    
    try:
        expiring = await db.get_expiring_subscriptions(REMINDER_DAYS)
        
        if not expiring:
            print(f"✅ Нет подписок, которые истекают в течение {REMINDER_DAYS} дней")
            await db.close()
            await test_bot.session.close()
            return
        
        print(f"📋 Найдено подписок, истекающих скоро: {len(expiring)}\n")
        
        for subscription in expiring:
            telegram_id = subscription["telegram_id"]
            end_date = subscription["end_date"]
            days_left = (end_date - datetime.now()).days
            
            print(f"⏰ Пользователь TG ID {telegram_id}")
            print(f"   Истекает: {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Осталось дней: {days_left}")
            
            try:
                keyboard = get_inline_keyboard_renew()
                await test_bot.send_message(
                    chat_id=telegram_id,
                    text=f"⏳ Ваша подписка заканчивается через {days_left} {'день' if days_left == 1 else 'дня' if days_left < 5 else 'дней'}.\n\n"
                         f"Продлите её чтобы не потерять доступ.",
                    reply_markup=keyboard
                )
                print(f"   ✅ Напоминание отправлено\n")
            except Exception as e:
                print(f"   ⚠️ Не удалось отправить: {e}\n")
        
        print("✅ Проверка завершена!")
        
    finally:
        await db.close()
        await test_bot.session.close()


async def show_active_subscriptions():
    """Показать активные подписки"""
    print("\n📊 === АКТИВНЫЕ ПОДПИСКИ ===\n")
    
    await db.init()
    
    async with db.pool.acquire() as conn:
        subscriptions = await conn.fetch(
            """
            SELECT s.*, u.telegram_id, u.first_name, u.username
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            WHERE s.status = 'active'
            ORDER BY s.end_date ASC
            """
        )
    
    if not subscriptions:
        print("✅ Нет активных подписок\n")
    else:
        print(f"Всего активных: {len(subscriptions)}\n")
        for sub in subscriptions:
            end_date = sub["end_date"]
            now = datetime.now()
            
            if end_date > now:
                time_left = end_date - now
                days = time_left.days
                hours = time_left.seconds // 3600
                minutes = (time_left.seconds % 3600) // 60
                
                print(f"👤 {sub['first_name']} (@{sub['username']})")
                print(f"   TG ID: {sub['telegram_id']}")
                print(f"   Истекает: {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Осталось: {days}д {hours}ч {minutes}м")
                print()
            else:
                print(f"⚠️ {sub['first_name']} - ИСТЕКЛА (будет удалена при проверке)")
                print()
    
    await db.close()


def print_help():
    print("""
🧪 === ТЕСТИРОВАНИЕ ЦИКЛА ПОДПИСКИ ===

Доступные команды:

1. Создать тестовую подписку:
   python test_subscription_cycle.py --create-test
   
   Создает подписку с коротким сроком (например, 2 минуты)
   для проверки автоматического удаления из канала.

2. Вручную проверить истекшие:
   python test_subscription_cycle.py --check-expired
   
   Находит все истекшие подписки и:
   - Удаляет пользователя из канала
   - Отправляет уведомление об истечении
   - Меняет статус на 'expired'

3. Проверить заканчивающиеся:
   python test_subscription_cycle.py --check-expiring
   
   Отправляет напоминания пользователям,
   у которых подписка истекает в ближайшие дни.

4. Показать активные подписки:
   python test_subscription_cycle.py --list
   
   Выводит список всех активных подписок
   с оставшимся временем.

📝 ПРИМЕЧАНИЯ:
   - Планировщик запускается автоматически вместе с ботом
   - check_expired - каждый день в 00:00
   - check_expiring - каждый день в 09:00
   - Эти команды нужны только для тестирования!
""")


async def main():
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    
    if command == "--create-test":
        await create_test_subscription()
    elif command == "--check-expired":
        await check_expired_now()
    elif command == "--check-expiring":
        await check_expiring_now()
    elif command == "--list":
        await show_active_subscriptions()
    else:
        print(f"❌ Неизвестная команда: {command}")
        print_help()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
