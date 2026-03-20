#!/usr/bin/env python3
"""
Скрипт для тестирования бота локально
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

# Проверить переменные окружения
def check_env_vars():
    print("🔍 Проверка переменных окружения...\n")
    
    required_vars = [
        'BOT_TOKEN',
        'ADMIN_ID',
        'CHANNEL_ID',
        'ROBOKASSA_MERCHANT_LOGIN',
        'ROBOKASSA_PASSWORD_1',
        'ROBOKASSA_PASSWORD_2',
        'DATABASE_URL'
    ]

    optional_vars = [
        'ROBOKASSA_TEST_PASSWORD_1',
        'ROBOKASSA_TEST_PASSWORD_2',
    ]
    
    all_ok = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked = value[:20] + '...' if len(value) > 20 else value
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: НЕ УСТАНОВЛЕНА")
            all_ok = False

    for var in optional_vars:
        value = os.getenv(var)
        if value:
            masked = value[:20] + '...' if len(value) > 20 else value
            print(f"✅ {var}: {masked}")
        else:
            print(f"ℹ️ {var}: не задана")
    
    print()
    return all_ok

# Проверить подключение к БД
async def test_database():
    print("🔍 Проверка подключения к БД...\n")
    
    try:
        from database import db
        await db.init()
        print("✅ Подключение к БД успешно")
        await db.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False

# Проверить токен бота
async def test_bot_token():
    print("\n🔍 Проверка токена бота...\n")
    
    try:
        from aiogram import Bot
        bot = Bot(token=os.getenv('BOT_TOKEN'))
        me = await bot.get_me()
        print(f"✅ Бот найден: @{me.username} (ID: {me.id})")
        await bot.session.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка токена бота: {e}")
        return False

# Проверить Robokassa
async def test_robokassa():
    print("\n🔍 Проверка Robokassa...\n")

    try:
        from robokassa_handler import robokassa

        payment = robokassa.create_payment(user_id=1, amount=100.0, description="test")
        if payment and payment.get("payment_url"):
            print("✅ Robokassa URL успешно формируется")
            print(f"   Payment ID: {payment.get('payment_id')}")

            if os.getenv('ROBOKASSA_TEST_PASSWORD_1') and os.getenv('ROBOKASSA_TEST_PASSWORD_2'):
                test_payment = robokassa.create_payment(
                    user_id=1,
                    amount=100.0,
                    description="test-store-check",
                    is_test=True,
                )
                print("✅ Тестовый Robokassa URL успешно формируется")
                print(f"   Test Payment ID: {test_payment.get('payment_id')}")
            return True
        print("❌ Robokassa не вернула payment_url")
        return False
    except Exception as e:
        print(f"❌ Ошибка Robokassa: {e}")
        return False

# Полный тест
async def run_tests():
    print("=" * 50)
    print("🧪 ТЕСТИРОВАНИЕ TELEGRAM БОТА")
    print("=" * 50)
    print()
    
    results = {
        "Переменные окружения": check_env_vars(),
        "Подключение к БД": await test_database(),
        "Токен бота": await test_bot_token(),
        "Robokassa": await test_robokassa()
    }
    
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 50)
    print()
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print()
    
    all_passed = all(results.values())
    if all_passed:
        print("🎉 Все тесты пройдены! Бот готов к запуску.")
        print("\nЗапустите бота командой:")
        print("  python3 main.py")
    else:
        print("⚠️  Некоторые тесты не пройдены. Проверьте ошибки выше.")
    
    return all_passed

if __name__ == "__main__":
    try:
        success = asyncio.run(run_tests())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n❌ Тестирование прерывано пользователем")
        exit(1)
