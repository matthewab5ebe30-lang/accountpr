import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/subscription_bot")

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://localhost")
WEBHOOK_PORT = int(os.getenv("PORT", os.getenv("WEBHOOK_PORT", "8443")))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/notification_url")


def _join_url(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")

SUBSCRIPTION_DAYS = 30
REMINDER_DAYS = 3

# Robokassa settings
ROBOKASSA_MERCHANT_LOGIN = os.getenv("ROBOKASSA_MERCHANT_LOGIN", "")
ROBOKASSA_PASSWORD_1 = os.getenv("ROBOKASSA_PASSWORD_1", "")
ROBOKASSA_PASSWORD_2 = os.getenv("ROBOKASSA_PASSWORD_2", "")
ROBOKASSA_TEST_PASSWORD_1 = os.getenv("ROBOKASSA_TEST_PASSWORD_1", "")
ROBOKASSA_TEST_PASSWORD_2 = os.getenv("ROBOKASSA_TEST_PASSWORD_2", "")
ROBOKASSA_IS_TEST = os.getenv("ROBOKASSA_IS_TEST", "1").lower() in {"1", "true", "yes", "on"}
ROBOKASSA_API_BASE = os.getenv("ROBOKASSA_API_BASE", "https://auth.robokassa.kz/Merchant/Index.aspx")
ROBOKASSA_TEST_BUTTON_ENABLED = bool(ROBOKASSA_TEST_PASSWORD_1 and ROBOKASSA_TEST_PASSWORD_2)

ROBOKASSA_RESULT_URL = _join_url(WEBHOOK_HOST, WEBHOOK_PATH)
ROBOKASSA_SUCCESS_URL = _join_url(WEBHOOK_HOST, "/payment/success")
ROBOKASSA_FAIL_URL = _join_url(WEBHOOK_HOST, "/payment/fail")

# Subscription price in RUB for Robokassa
SUBSCRIPTION_PRICE = float(os.getenv("SUBSCRIPTION_PRICE", "150.00"))
SUBSCRIPTION_PRICE_TEXT = (
    str(int(SUBSCRIPTION_PRICE)) if float(SUBSCRIPTION_PRICE).is_integer() else f"{SUBSCRIPTION_PRICE:g}"
)
CURRENCY = "RUB"
