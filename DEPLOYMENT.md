# Инструкция по развёртыванию Telegram бота

## Локальное развёртывание

### Требования

- Python 3.8+
- PostgreSQL 12+
- pip

### Шаги

```bash
# 1. Клонируйте репозиторий
git clone https://github.com/yourusername/accountpr.git
cd accountpr

# 2. Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Установите зависимости
pip install -r requirements.txt

# 4. Создайте базу данных PostgreSQL
createdb subscription_bot

# 5. Скопируйте и отредактируйте .env
cp .env.example .env
# Отредактируйте .env с вашими данными

# 6. Запустите бота
python3 main.py
```

## Docker развёртывание

### Requirements

- Docker
- Docker Compose

### Шаги

```bash
# 1. Скопируйте .env
cp .env.example .env

# 2. Отредактируйте .env
nano .env

# 3. Запустите с Docker Compose
docker-compose up -d

# 4. Проверьте логи
docker-compose logs -f bot
```

## Production развёртывание на Linux

### Требования

- VPS с Ubuntu 20.04+
- Домен (опционально, но рекомендуется)
- SSL сертификат (Let's Encrypt бесплатно)

### Шаги

```bash
# 1. Обновите систему
sudo apt update && sudo apt upgrade -y

# 2. Установите PostgreSQL
sudo apt install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 3. Создайте базу и пользователя
sudo -u postgres psql -c "CREATE DATABASE subscription_bot;"
sudo -u postgres psql -c "CREATE USER subscription_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "ALTER ROLE subscription_user SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE subscription_user SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE subscription_user SET default_transaction_deferrable TO on;"
sudo -u postgres psql -c "ALTER ROLE subscription_user SET default_transaction_read_committed TO on;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE subscription_bot TO subscription_user;"

# 4. Установите Python и зависимости
sudo apt install python3 python3-pip python3-venv git -y

# 5. Создайте пользователя для бота
sudo useradd -m -d /home/bot bot

# 6. Клонируйте репозиторий
sudo -u bot git clone https://github.com/yourusername/accountpr.git /home/bot/accountpr
cd /home/bot/accountpr

# 7. Создайте виртуальное окружение
sudo -u bot python3 -m venv /home/bot/accountpr/venv
sudo -u bot /home/bot/accountpr/venv/bin/pip install -r requirements.txt

# 8. Скопируйте и отредактируйте .env
sudo -u bot cp .env.example /home/bot/accountpr/.env
sudo -u bot nano /home/bot/accountpr/.env

# 9. Установите Nginx
sudo apt install nginx -y

# 10. Скопируйте конфигурацию Nginx
sudo cp nginx.conf /etc/nginx/sites-available/telegram-bot
sudo ln -s /etc/nginx/sites-available/telegram-bot /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# Отредактируйте конфигурацию
sudo nano /etc/nginx/sites-available/telegram-bot

# Проверьте синтаксис
sudo nginx -t

# Перезагрузите Nginx
sudo systemctl restart nginx

# 11. Установите SSL с Let's Encrypt (опционально, но рекомендуется)
sudo apt install certbot python3-certbot-nginx -y
sudo certbot certonly --nginx -d your-domain.com

# 12. Установите systemd сервис
sudo cp subscription-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start subscription-bot
sudo systemctl enable subscription-bot

# 13. Проверьте статус
sudo systemctl status subscription-bot
```

### Команды для управления

```bash
# Посмотреть статус
sudo systemctl status subscription-bot

# Просмотр логов
sudo journalctl -u subscription-bot -f

# Перезагрузить бота
sudo systemctl restart subscription-bot

# Остановить бота
sudo systemctl stop subscription-bot

# Запустить бота
sudo systemctl start subscription-bot
```

## Мониторинг и логирование

### Логирование в файл

Отредактируйте `main.py`:

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
```

### Ротация логов

Создайте `/etc/logrotate.d/telegram-bot`:

```
/home/bot/accountpr/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 0644 bot bot
    sharedscripts
    postrotate
        systemctl reload subscription-bot > /dev/null 2>&1 || true
    endscript
}
```

## Backup базы данных

### Ручной backup

```bash
pg_dump -U subscription_user -d subscription_bot > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Автоматический backup (ежедневно)

Добавьте в crontab:

```bash
0 2 * * * /usr/bin/pg_dump -U subscription_user -d subscription_bot > /home/bot/backups/backup_$(date +\%Y\%m\%d).sql
```

## Troubleshooting

### Бот не стартует

```bash
# Проверьте логи
sudo journalctl -u subscription-bot -n 50

# Проверьте .env переменные
cat /home/bot/accountpr/.env

# Проверьте подключение к БД
psql -U subscription_user -d subscription_bot -c "SELECT 1;"
```

### Webhook не работает

```bash
# Проверьте, что Nginx запущен
sudo systemctl status nginx

# Проверьте конфигурацию Nginx
sudo nginx -t

# Проверьте логи Nginx
sudo tail -f /var/log/nginx/error.log
```

### Robokassa callback не активирует подписку

Проверьте:

- ROBOKASSA_PASSWORD_1 и ROBOKASSA_PASSWORD_2 в `.env`
- соответствие Result URL в кабинете Robokassa и `WEBHOOK_HOST` + `WEBHOOK_PATH`
- доступность пути `/notification_url` извне
- логи `webhook_app.py`

### Дискотека платежей

```bash
# Проверьте логи бота
sudo journalctl -u subscription-bot -f

# Проверьте таблицу payments
psql -U subscription_user -d subscription_bot -c "SELECT * FROM payments;"
```

## Production Checklist

- [x] Установлена Production БД (не SQLite)
- [x] Настроены переменные окружения (.env)
- [x] Включен SSL сертификат
- [x] Настроено логирование
- [x] Настроены резервные копии
- [x] Установлен systemd сервис
- [x] Настроен Nginx как reverse proxy
- [x] Включен мониторинг
- [x] Протестированы все функции
- [x] Настроена ротация логов
