#!/bin/bash

# Быстрый старт Telegram бота

set -e

echo "================================"
echo "🚀 БЫСТРЫЙ СТАРТ TELEGRAM БОТА"
echo "================================"
echo ""

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функции
log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# Шаг 1: Проверка Python
echo ""
log_info "Шаг 1: Проверка Python"
if ! command -v python3 &> /dev/null; then
    log_error "Python3 не установлен"
    echo "Установите Python3 и попробуйте снова"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
log_success "Python $PYTHON_VERSION найден"

# Шаг 2: Проверка PostgreSQL
echo ""
log_info "Шаг 2: Проверка PostgreSQL"
if ! command -v psql &> /dev/null; then
    log_error "PostgreSQL клиент не установлен"
    echo "Установите PostgreSQL и попробуйте снова"
    exit 1
fi
log_success "PostgreSQL клиент найден"

# Шаг 3: Проверка .env
echo ""
log_info "Шаг 3: Проверка .env файла"
if [ ! -f .env ]; then
    if [ ! -f .env.example ]; then
        log_error ".env.example не найден"
        exit 1
    fi
    log_info "Создаю .env из .env.example"
    cp .env.example .env
    log_info "Файл .env создан. ОТРЕДАКТИРУЙТЕ ЕГО ПЕРЕД ЗАПУСКОМ!"
    echo ""
    echo "Необходимые переменные:"
    echo "  • BOT_TOKEN - токен Telegram бота"
    echo "  • ADMIN_ID - ваш Telegram ID"
    echo "  • CHANNEL_ID - ID приватного канала"
    echo "  • ROBOKASSA_MERCHANT_LOGIN - логин магазина Robokassa"
    echo "  • ROBOKASSA_PASSWORD_1 - пароль #1"
    echo "  • ROBOKASSA_PASSWORD_2 - пароль #2"
    echo "  • DATABASE_URL - URL для подключения к PostgreSQL"
    echo ""
    echo "Отредактируйте .env и запустите снова:"
    echo "  nano .env"
    exit 1
fi
log_success ".env найден"

# Шаг 4: Создание виртуального окружения
echo ""
log_info "Шаг 4: Создание virtual environment"
if [ ! -d venv ]; then
    python3 -m venv venv
    log_success "Virtual environment создан"
else
    log_success "Virtual environment уже существует"
fi

# Шаг 5: Активация виртуального окружения
echo ""
log_info "Шаг 5: Активация virtual environment"
source venv/bin/activate
log_success "Virtual environment активирован"

# Шаг 6: Установка зависимостей
echo ""
log_info "Шаг 6: Установка зависимостей"
pip install --upgrade pip wheel setuptools > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
log_success "Зависимости установлены"

# Шаг 7: Проверка подключения к БД
echo ""
log_info "Шаг 7: Проверка подключения к БД"

# Парсим DATABASE_URL
if ! grep -q "DATABASE_URL=" .env; then
    log_error "DATABASE_URL не найден в .env"
    exit 1
fi

DB_URL=$(grep "^DATABASE_URL=" .env | cut -d'=' -f2)

# Проверяем подключение
if psql "$DB_URL" -c "SELECT 1" > /dev/null 2>&1; then
    log_success "Подключение к БД работает"
else
    log_error "Не удалось подключиться к БД"
    echo "Проверьте DATABASE_URL в .env файле"
    exit 1
fi

# Шаг 8: Проверка таблиц
echo ""
log_info "Шаг 8: Проверка таблиц БД"
if python3 -c "
import asyncio
from database import db

async def check():
    await db.init()
    await db.close()

try:
    asyncio.run(check())
except Exception as e:
    print(f'❌ Ошибка: {e}')
    exit(1)
" 2>/dev/null; then
    log_success "Таблицы БД готовы"
else
    log_error "Ошибка при проверке таблиц"
    exit 1
fi

# Шаг 9: Test bot
echo ""
log_info "Шаг 9: Тестирование конфигурации"
python3 test_bot.py

# Финиш
echo ""
echo "================================"
log_success "🎉 БОТ ГОТОВ К ЗАПУСКУ!"
echo "================================"
echo ""
echo "Проверьте что все тесты пройдены выше ⬆️"
echo ""
echo "Для запуска бота выполните:"
echo "  python3 main.py"
echo ""
echo "Или используйте скрипт:"
echo "  bash run.sh"
echo ""
echo "================================"
