import logging
from pathlib import Path

from aiohttp import web
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import CHANNEL_ID, SUBSCRIPTION_DAYS, WEBHOOK_PATH
from database import db
from robokassa_handler import robokassa

logger = logging.getLogger(__name__)
bot: Bot | None = None

PROJECT_DIR = Path(__file__).resolve().parent
LEGAL_DIR = PROJECT_DIR / "public" / "legal"
OFFER_FILES_PRIORITY = ("oferta.pdf", "oferta.html", "oferta.md")


async def set_bot(bot_instance: Bot):
    global bot
    bot = bot_instance


async def _send_channel_link(telegram_id: int) -> bool:
    if bot is None:
        return False

    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            member_limit=1,
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🟢 Перейти в канал", url=invite_link.invite_link)],
                [InlineKeyboardButton(text="🏠 Меню", callback_data="menu")],
            ]
        )
        await bot.send_message(
            chat_id=telegram_id,
            text="✅ Оплата прошла успешно!\n\nДобро пожаловать в канал.",
            reply_markup=keyboard,
        )
        return True
    except Exception as e:
        logger.warning("Failed to send invite link to telegram_id=%s: %s", telegram_id, e)
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text="✅ Оплата прошла успешно! Подписка активирована. Откройте бота и нажмите /start.",
            )
            return True
        except Exception as send_error:
            logger.warning("Failed fallback payment message to telegram_id=%s: %s", telegram_id, send_error)
            return False


def _get_param(data: dict[str, str], key: str) -> str:
    return data.get(key, "") or data.get(key.lower(), "")


async def robokassa_result_handler(request: web.Request) -> web.Response:
    """
    ResultURL handler.
    Robokassa expects plain text response: OK<InvId>
    """
    try:
        data = dict(request.query)
        if request.method == "POST":
            post_data = await request.post()
            data.update(dict(post_data))

        out_sum = _get_param(data, "OutSum")
        inv_id = _get_param(data, "InvId")
        signature = _get_param(data, "SignatureValue")

        if not out_sum or not inv_id or not signature:
            logger.warning("Robokassa ResultURL: missing required params data=%s", data)
            return web.Response(status=400, text="Missing parameters")

        if not robokassa.verify_result_signature(out_sum, inv_id, signature):
            logger.warning("Robokassa ResultURL: bad signature inv_id=%s", inv_id)
            return web.Response(status=403, text="Bad signature")

        payment = await db.get_payment_by_external_id(inv_id)
        if not payment:
            logger.warning("Robokassa ResultURL: payment not found inv_id=%s", inv_id)
            return web.Response(status=404, text="Payment not found")

        if payment["status"] == "succeeded":
            return web.Response(status=200, text=f"OK{inv_id}")

        if abs(float(payment["amount"]) - float(out_sum)) > 0.0001:
            logger.error(
                "Robokassa amount mismatch inv_id=%s db=%s callback=%s",
                inv_id,
                payment["amount"],
                out_sum,
            )
            return web.Response(status=400, text="Amount mismatch")

        await db.update_payment_status(inv_id, "succeeded")
        await db.activate_subscription_from_payment(
            user_id=payment["user_id"],
            payment_id=payment["id"],
            days=SUBSCRIPTION_DAYS,
        )

        user = await db.get_user_by_id(payment["user_id"])
        if user and bot:
            delivered = await _send_channel_link(user["telegram_id"])
            if delivered:
                await db.mark_payment_notified(inv_id)

        logger.info("Robokassa payment processed inv_id=%s user=%s", inv_id, payment["user_id"])
        return web.Response(status=200, text=f"OK{inv_id}")

    except Exception as e:
        logger.exception("Robokassa ResultURL error: %s", e)
        return web.Response(status=500, text="Internal Server Error")


async def robokassa_success_handler(request: web.Request) -> web.Response:
    inv_id = request.query.get("InvId", "")
    return web.Response(
        text=f"Оплата подтверждена. Вернитесь в Telegram-бот и нажмите /start. ID платежа: {inv_id}"
    )


async def robokassa_fail_handler(request: web.Request) -> web.Response:
    inv_id = request.query.get("InvId", "")
    if inv_id:
        try:
            await db.update_payment_status(inv_id, "failed")
        except Exception as e:
            logger.warning("Failed to mark payment failed for inv_id=%s: %s", inv_id, e)
    return web.Response(text="Оплата отменена или не завершена. Вернитесь в Telegram-бот.")


async def hello_handler(request: web.Request) -> web.Response:
    return web.Response(text="Robokassa webhook is running.")


async def oferta_handler(request: web.Request) -> web.Response:
    for file_name in OFFER_FILES_PRIORITY:
        offer_path = LEGAL_DIR / file_name
        if offer_path.is_file():
            return web.FileResponse(path=offer_path)
    return web.Response(
        status=404,
        text="Оферта не загружена. Добавьте файл oferta.pdf, oferta.html или oferta.md в папку public/legal.",
    )


def create_app() -> web.Application:
    app = web.Application()
    LEGAL_DIR.mkdir(parents=True, exist_ok=True)
    app.router.add_get("/", hello_handler)
    app.router.add_get("/oferta", oferta_handler)
    app.router.add_static("/legal/", path=str(LEGAL_DIR), show_index=True)
    app.router.add_get("/payment/success", robokassa_success_handler)
    app.router.add_get("/payment/fail", robokassa_fail_handler)
    app.router.add_get(WEBHOOK_PATH, robokassa_result_handler)
    app.router.add_post(WEBHOOK_PATH, robokassa_result_handler)
    return app
