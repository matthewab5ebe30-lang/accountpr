#!/bin/bash

if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Создаю из .env.example"
    cp .env.example .env
    echo "✅ Файл .env создан. Пожалуйста, отредактируйте его с вашими данными."
    echo "Необходимые переменные:"
    echo "  BOT_TOKEN - токен вашего Telegram бота"
    echo "  ADMIN_ID - ваш Telegram ID (админ)"
    echo "  CHANNEL_ID - ID вашего приватного канала"
    echo "  ROBOKASSA_MERCHANT_LOGIN - логин магазина Robokassa"
    echo "  ROBOKASSA_PASSWORD_1 - пароль #1 (для формирования ссылки)"
    echo "  ROBOKASSA_PASSWORD_2 - пароль #2 (для Result URL)"
    echo "  DATABASE_URL - URL для подключения к PostgreSQL"
    echo ""
    echo "После редактирования .env запустите снова:"
    echo "  bash run.sh"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не установлен"
    exit 1
fi

if ! python3 -c "import venv" 2>/dev/null; then
    echo "❌ Python venv модуль не найден"
    exit 1
fi

if [ ! -d venv ]; then
    echo "📦 Создаю virtual environment..."
    python3 -m venv venv
fi

echo "🔧 Активирую virtual environment..."
source venv/bin/activate

echo "📥 Устанавливаю зависимости..."
pip install --upgrade pip wheel setuptools > /dev/null 2>&1
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Зависимости установлены"
    echo ""
    echo "🚀 Запускаю Telegram бота..."
    python3 main.py
else
    echo "❌ Ошибка при установке зависимостей"
    exit 1
fi
