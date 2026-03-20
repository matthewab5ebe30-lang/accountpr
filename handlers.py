"""Telegram bot message and callback handlers"""
import logging
from datetime import datetime
from pathlib import Path

from aiogram import F, Router, types
from aiogram.filters import Command, CommandStart
from aiogram.types import FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import (
    ADMIN_ID,
    CHANNEL_ID,
    REMINDER_DAYS,
    SUBSCRIPTION_DAYS,
    SUBSCRIPTION_PRICE,
    SUBSCRIPTION_PRICE_TEXT,
    ROBOKASSA_TEST_BUTTON_ENABLED,
    WEBHOOK_HOST,
)
from database import db
from robokassa_handler import robokassa

logger = logging.getLogger(__name__)
router = Router()

PRICE_TEXT = SUBSCRIPTION_PRICE_TEXT
OFFERTA_URL = WEBHOOK_HOST.rstrip("/") + "/oferta"


def get_main_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Купить подписку", callback_data="buy_subscription")
    kb.button(text="ℹ️ Информация", callback_data="info")
    if ROBOKASSA_TEST_BUTTON_ENABLED:
        kb.button(text="🧪 Тестовый платеж", callback_data="test_payment")
    kb.adjust(1)
    return kb.as_markup()


def get_payment_keyboard(payment_url: str, is_test: bool = False) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    button_text = "🧪 Открыть тестовую оплату" if is_test else "💳 Перейти к оплате"
    kb.button(text=button_text, url=payment_url)
    kb.button(text="🏠 Меню", callback_data="menu")
    kb.button(text="❌ Отмена", callback_data="cancel_payment")
    kb.adjust(1)
    return kb.as_markup()


def get_inline_keyboard_renew(channel_link: str | None = None) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if channel_link:
        kb.button(text="🟢 Перейти в канал", url=channel_link)
    kb.button(text="🔵 Продлить подписку", callback_data="renew_subscription")
    kb.button(text="ℹ️ Информация", callback_data="info")
    if ROBOKASSA_TEST_BUTTON_ENABLED:
        kb.button(text="🧪 Тестовый платеж", callback_data="test_payment")
    kb.button(text="🔴 Отменить подписку", callback_data="cancel_active_subscription")
    kb.button(text="🏠 Меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def get_success_keyboard(channel_link: str) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🟢 Перейти в канал", url=channel_link)
    kb.button(text="🏠 Меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def get_menu_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def get_info_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📄 Скачать оферту", callback_data="download_oferta")
    kb.button(text="🏠 Меню", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def get_cancel_confirm_keyboard() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, отменить", callback_data="confirm_cancel_subscription")
    kb.button(text="❌ Нет, оставить", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


async def _ensure_user(from_user: types.User):
    user = await db.get_user_by_telegram_id(from_user.id)
    if user:
        return user
    new_user_id = await db.add_user(
        telegram_id=from_user.id,
        username=from_user.username or "unknown",
        first_name=from_user.first_name or "",
        last_name=from_user.last_name or "",
    )
    if not new_user_id:
        return None
    return await db.get_user_by_telegram_id(from_user.id)


@router.callback_query(F.data == "info")
async def info_callback(query: types.CallbackQuery):
    try:
        text = (
            "ℹ️ Информация\n\n"
            "1) О товаре\n"
            "Вы приобретаете подписку на закрытый тг канал Go с Margo.\n\n"
            "2) Стоимость\n"
            f"{PRICE_TEXT} руб. за месяц с момента подключения подписки.\n"
            "Рустемова Маргарита Викторовна\n"
            "ИНН 235209936420\n"
            "г. Москва\n\n"
            "3) Контакты\n"
            "Телефон: +79999798399\n"
            "тг: @Margosha868\n\n"
            "4) Отказ от продления\n"
            "Вы можете отказаться от продления подписки. Оформленная подписка будет доступна до конца проплаченного периода.\n\n"
            "5) Оферта\n"
            "Нажмите кнопку ниже, чтобы скачать файл оферты.\n\n"
            "6) Условия возврата\n"
            "Возврат средств осуществляется в соответствии с действующим законодательством.\n"
            "Для оформления возврата необходимо обратиться к администратору: @Margosha868\n"
            "В сообщении укажите причину обращения и данные, подтверждающие оплату.\n\n"
            "Заявка рассматривается в индивидуальном порядке.\n"
            "Срок рассмотрения - до 3 рабочих дней\n\n"
            "При одобрении возврата средства возвращаются в течении 5-10 рабочих дней, тем же способом, которым была произведена оплата."
        )

        await query.message.edit_text(text, reply_markup=get_info_keyboard())
        await query.answer()
    except Exception as e:
        logger.error("Error in info_callback: %s", e)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "download_oferta")
async def download_oferta_callback(query: types.CallbackQuery):
    try:
        await query.answer()
        project_dir = Path(__file__).resolve().parent
        legal_dir = project_dir / "public" / "legal"
        for file_name in ("oferta.pdf", "oferta.html", "oferta.md"):
            offer_path = legal_dir / file_name
            if offer_path.is_file():
                await query.message.answer_document(
                    FSInputFile(offer_path, filename="oferta.pdf"),
                    caption="📄 Оферта",
                )
                return
        await query.message.answer("❌ Файл оферты не найден. Обратитесь к администратору.")
    except Exception as e:
        logger.error("Error in download_oferta_callback: %s", e)
        await query.answer("❌ Не удалось отправить файл", show_alert=True)


@router.callback_query(F.data == "menu")
async def menu_callback(query: types.CallbackQuery):
    try:
        await query.answer()
        user = await _ensure_user(query.from_user)
        if not user:
            return

        active_sub = await db.get_active_subscription(user["id"])
        if active_sub:
            end_date = active_sub["end_date"]
            days_left = (end_date - datetime.now()).days

            invite_url = None
            try:
                invite = await query.bot.create_chat_invite_link(
                    chat_id=CHANNEL_ID,
                    member_limit=1,
                )
                invite_url = invite.invite_link
            except Exception as invite_error:
                logger.warning("Failed to create invite link: %s", invite_error)

            text = (
                "🏠 Главное меню\n\n"
                "✅ У вас активная подписка\n"
                f"📅 Истекает: {end_date.strftime('%d.%m.%Y')}\n"
                f"⏱️ Дней осталось: {days_left}\n\n"
                "Что вы хотите сделать?"
            )
            await query.message.edit_text(text, reply_markup=get_inline_keyboard_renew(invite_url))
        else:
            text = (
                "🏠 Главное меню\n\n"
                "Ваша подписка неактивна.\n"
                f"💰 Стоимость подписки: {PRICE_TEXT} руб. за 30 дней\n"
                f"Оплачивая {PRICE_TEXT} руб., вы приобретаете доступ в ТГ канал."
            )
            if ROBOKASSA_TEST_BUTTON_ENABLED:
                text += "\n\nДля проверки магазина доступна отдельная кнопка тестового платежа."
            await query.message.edit_text(text, reply_markup=get_main_keyboard())

    except Exception as e:
        logger.error("Error in menu_callback: %s", e)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(CommandStart())
async def start(message: types.Message):
    try:
        user = await _ensure_user(message.from_user)
        if not user:
            await message.answer("❌ Не удалось зарегистрировать. Попробуйте снова через минуту.")
            return

        unnotified = await db.get_latest_unnotified_succeeded_payment_by_user(user["id"])
        if unnotified:
            active_sub = await db.get_active_subscription(user["id"])
            end_date = active_sub["end_date"] if active_sub else datetime.utcnow()
            try:
                invite = await message.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
                await message.answer(
                    "✅ Оплата прошла успешно!\n\n"
                    f"📅 Подписка активна до: {end_date.strftime('%d.%m.%Y')}\n\n"
                    "Нажмите кнопку ниже, чтобы перейти в канал.",
                    reply_markup=get_success_keyboard(invite.invite_link),
                )
            except Exception as e:
                logger.warning("Failed to create invite in /start catch-up: %s", e)
                await message.answer(
                    "✅ Оплата прошла успешно! Подписка активирована. Откройте меню.",
                    reply_markup=get_menu_keyboard(),
                )
            await db.mark_all_unnotified_succeeded_by_user(user["id"])
            return

        active_sub = await db.get_active_subscription(user["id"])
        if active_sub:
            end_date = active_sub["end_date"]
            days_left = (end_date - datetime.now()).days
            invite_url = None
            try:
                invite = await message.bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=1)
                invite_url = invite.invite_link
            except Exception as e:
                logger.warning("Failed to create invite link: %s", e)
            await message.answer(
                f"Добро пожаловать, {message.from_user.first_name}!\n\n"
                "Go с Марго - это закрытое сообщество для общения, знакомств и совместного времяпрепровождения.\n\n"
                "В канале участники:\n"
                "-общаются в дружелюбной атмосфере\n"
                "-находят новых знакомых и единомышленников\n"
                "-участвуют в офлайн встречах\n"
                "-получают доступ к анонсам мероприятий и активности внутри сообщества\n\n"
                "Канал создан для людей, которым важно живое общение, новые знакомства и интересный досуг.\n\n"
                "✅ У вас активная подписка\n"
                f"📅 Истекает: {end_date.strftime('%d.%m.%Y')}\n"
                f"⏱️ Дней осталось: {days_left}\n\n"
                "Что вы хотите сделать?",
                reply_markup=get_inline_keyboard_renew(invite_url),
            )
        else:
            await message.answer(
                f"Добро пожаловать, {message.from_user.first_name}!\n\n"
                "Go с Марго - это закрытое сообщество для общения, знакомств и совместного времяпрепровождения.\n\n"
                "В канале участники:\n"
                "-общаются в дружелюбной атмосфере\n"
                "-находят новых знакомых и единомышленников\n"
                "-участвуют в офлайн встречах\n"
                "-получают доступ к анонсам мероприятий и активности внутри сообщества\n\n"
                "Канал создан для людей, которым важно живое общение, новые знакомства и интересный досуг.\n\n"
                "📺 Подпишитесь на наш эксклюзивный канал\n"
                f"💰 Стоимость подписки: {PRICE_TEXT} руб. в месяц\n"
                f"Оплачивая {PRICE_TEXT} руб., вы приобретаете доступ в ТГ канал на 30 дней.\n\n"
                + ("Также доступна отдельная кнопка тестового платежа для проверки сервиса.\n\n" if ROBOKASSA_TEST_BUTTON_ENABLED else "")
                + "Нажмите кнопку ниже, чтобы купить подписку",
                reply_markup=get_main_keyboard(),
            )

    except Exception as e:
        logger.error("Error in start handler: %s", e)
        await message.answer("❌ Ошибка инициализации. Попробуйте снова.")


@router.callback_query(F.data == "buy_subscription")
async def buy_subscription(query: types.CallbackQuery):
    try:
        await query.answer()
        user = await _ensure_user(query.from_user)
        if not user:
            return

        payment = robokassa.create_payment(
            user_id=user["id"],
            amount=SUBSCRIPTION_PRICE,
            description="Подписка на канал на 30 дней",
            is_test=False,
        )

        await db.create_payment(
            user_id=user["id"],
            external_payment_id=payment["payment_id"],
            amount=SUBSCRIPTION_PRICE,
            currency="RUB",
        )

        text = (
            f"💰 Подписка: {PRICE_TEXT} руб. за 30 дней\n"
            f"Оплачивая {PRICE_TEXT} руб., вы приобретаете доступ в ТГ канал.\n\n"
            "Нажмите кнопку ниже, чтобы открыть страницу оплаты.\n\n"
            "После успешной оплаты подписка активируется автоматически."
        )
        await query.message.edit_text(text, reply_markup=get_payment_keyboard(payment["payment_url"]))

    except Exception as e:
        logger.error("Error in buy_subscription: %s", e)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "test_payment")
async def test_payment(query: types.CallbackQuery):
    try:
        await query.answer()
        user = await _ensure_user(query.from_user)
        if not user:
            return

        payment = robokassa.create_payment(
            user_id=user["id"],
            amount=SUBSCRIPTION_PRICE,
            description="Тестовый платеж Robokassa для проверки магазина",
            is_test=True,
        )

        await db.create_payment(
            user_id=user["id"],
            external_payment_id=payment["payment_id"],
            amount=SUBSCRIPTION_PRICE,
            currency="RUB",
        )

        text = (
            "🧪 Тестовый платеж Robokassa\n\n"
            "Эта кнопка создана для тестового магазина и проверки сервиса Robokassa.\n"
            f"Сумма тестового платежа: {PRICE_TEXT} руб.\n\n"
            "Нажмите кнопку ниже, чтобы открыть тестовую страницу оплаты.\n\n"
            "После успешного callback тестовый платеж будет обработан тем же сценарием, что и обычный."
        )
        await query.message.edit_text(text, reply_markup=get_payment_keyboard(payment["payment_url"], is_test=True))

    except Exception as e:
        logger.error("Error in test_payment: %s", e)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "renew_subscription")
async def renew_subscription(query: types.CallbackQuery):
    try:
        await query.answer()
        user = await db.get_user_by_telegram_id(query.from_user.id)
        if not user:
            return

        active_sub = await db.get_active_subscription(user["id"])
        if not active_sub:
            return

        payment = robokassa.create_payment(
            user_id=user["id"],
            amount=SUBSCRIPTION_PRICE,
            description="Продление подписки на канал на 30 дней",
            is_test=False,
        )

        await db.create_payment(
            user_id=user["id"],
            external_payment_id=payment["payment_id"],
            amount=SUBSCRIPTION_PRICE,
            currency="RUB",
        )

        text = (
            f"🔄 Продление подписки: {PRICE_TEXT} руб. за 30 дней\n\n"
            f"Текущая подписка истекает: {active_sub['end_date'].strftime('%d.%m.%Y')}\n\n"
            "Нажмите кнопку ниже, чтобы открыть страницу оплаты.\n\n"
            "После успешной оплаты продление активируется автоматически."
        )
        await query.message.edit_text(text, reply_markup=get_payment_keyboard(payment["payment_url"]))

    except Exception as e:
        logger.error("Error in renew_subscription: %s", e)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(query: types.CallbackQuery):
    try:
        await query.message.edit_text(
            "❌ Платеж отменен\n\n"
            "Если у вас есть вопросы, свяжитесь с поддержкой.",
            reply_markup=get_menu_keyboard(),
        )
        await query.answer()
    except Exception as e:
        logger.error("Error in cancel_payment: %s", e)
        await query.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "cancel_active_subscription")
async def cancel_active_subscription(query: types.CallbackQuery):
    try:
        await query.answer()
        user = await db.get_user_by_telegram_id(query.from_user.id)
        if not user:
            return

        active_sub = await db.get_active_subscription(user["id"])
        if not active_sub:
            return

        end_date = active_sub["end_date"]
        text = (
            "⚠️ Вы уверены, что хотите отменить подписку?\n\n"
            f"📅 Текущая подписка действует до: {end_date.strftime('%d.%m.%Y')}\n\n"
            "После отмены доступ в канал останется до окончания текущего периода, "
            "затем будет закрыт автоматически."
        )
        await query.message.edit_text(text, reply_markup=get_cancel_confirm_keyboard())

    except Exception as e:
        logger.error("Error in cancel_active_subscription: %s", e)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.callback_query(F.data == "confirm_cancel_subscription")
async def confirm_cancel_subscription(query: types.CallbackQuery):
    try:
        await query.answer()
        user = await db.get_user_by_telegram_id(query.from_user.id)
        if not user:
            return

        active_sub = await db.get_active_subscription(user["id"])
        if not active_sub:
            return

        end_date = active_sub["end_date"]
        await db.cancel_subscription(active_sub["id"])

        text = (
            "❌ Ваша подписка отменена.\n\n"
            f"❗️ Доступ в канал остаётся до {end_date.strftime('%d.%m.%Y')}\n"
            "После этой даты доступ будет закрыт автоматически."
        )
        await query.message.edit_text(text, reply_markup=get_menu_keyboard())
        await query.answer("✅ Подписка отменена", show_alert=True)
        logger.info("User %s cancelled active subscription", user["id"])

    except Exception as e:
        logger.error("Error in confirm_cancel_subscription: %s", e)
        await query.answer(f"❌ Ошибка: {str(e)}", show_alert=True)


@router.message(Command("stats"))
async def stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен")
        return
    try:
        s = await db.get_stats()
        text = (
            "📊 Статистика бота\n\n"
            f"👥 Всего пользователей: {s['total_users']}\n"
            f"✅ Активных подписок: {s['active_subscriptions']}\n"
            f"💰 Общая выручка: {s['total_revenue']:.2f} руб."
        )
        await message.answer(text)
    except Exception as e:
        logger.error("Error in stats: %s", e)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("users"))
async def users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен")
        return
    try:
        users_list = await db.get_all_users()
        text = f"👥 Всего пользователей: {len(users_list)}\n\n"
        for user in users_list[:10]:
            text += f"• {user['first_name']} (@{user['username']})\n"
        if len(users_list) > 10:
            text += f"\n... и ещё {len(users_list) - 10}"
        await message.answer(text)
    except Exception as e:
        logger.error("Error in users: %s", e)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("broadcast"))
async def broadcast(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен")
        return

    if not message.text or not message.text.startswith("/broadcast "):
        return

    try:
        broadcast_text = message.text.replace("/broadcast ", "", 1)
        users_list = await db.get_all_users()

        for user in users_list:
            try:
                from main import bot

                await bot.send_message(user["telegram_id"], broadcast_text)
            except Exception as e:
                logger.warning("Failed to send message to user %s: %s", user["id"], e)

        await message.answer(f"✅ Сообщение отправлено {len(users_list)} пользователям")
    except Exception as e:
        logger.error("Error in broadcast: %s", e)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("test_expired"))
async def test_check_expired(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен")
        return
    try:
        expired = await db.get_expired_subscriptions()

        if not expired:
            await message.answer("✅ Нет истекших подписок")
            return

        await message.answer(f"🔍 Найдено истекших подписок: {len(expired)}\n\nОбработка...")

        removed = 0
        errors = 0

        for subscription in expired:
            telegram_id = subscription["telegram_id"]
            user_id = subscription["user_id"]

            try:
                await db.expire_subscription(user_id)

                try:
                    await message.bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=telegram_id)
                    await message.bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=telegram_id)
                    removed += 1
                except Exception as remove_err:
                    logger.warning("Could not remove user %s: %s", telegram_id, remove_err)
                    errors += 1

                try:
                    await message.bot.send_message(
                        chat_id=telegram_id,
                        text="❌ Ваша подписка истекла.\n\nДоступ к каналу был закрыт.\n\nВы можете купить новую подписку в любой момент.",
                    )
                except Exception:
                    pass

            except Exception as e:
                logger.error("Error processing expired subscription: %s", e)
                errors += 1

        result = f"✅ Обработано: {len(expired)}\n"
        result += f"🚫 Удалено из канала: {removed}\n"
        if errors > 0:
            result += f"⚠️ Ошибок: {errors}"

        await message.answer(result)

    except Exception as e:
        logger.error("Error in test_check_expired: %s", e)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message(Command("test_expiring"))
async def test_check_expiring(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Доступ запрещен")
        return
    try:
        expiring = await db.get_expiring_subscriptions(REMINDER_DAYS)

        if not expiring:
            await message.answer(f"✅ Нет подписок, истекающих в течение {REMINDER_DAYS} дней")
            return

        await message.answer(f"⏰ Найдено подписок: {len(expiring)}\n\nОтправка напоминаний...")

        sent = 0
        errors = 0

        for subscription in expiring:
            telegram_id = subscription["telegram_id"]
            end_date = subscription["end_date"]
            days_left = (end_date - datetime.now()).days

            try:
                keyboard = get_inline_keyboard_renew()
                await message.bot.send_message(
                    chat_id=telegram_id,
                    text=f"⏳ Ваша подписка заканчивается через {days_left} {'день' if days_left == 1 else 'дня' if days_left < 5 else 'дней'}.\n\n"
                    "Продлите её чтобы не потерять доступ.",
                    reply_markup=keyboard,
                )
                sent += 1
            except Exception as e:
                logger.warning("Failed to send reminder to %s: %s", telegram_id, e)
                errors += 1

        result = f"✅ Напоминаний отправлено: {sent}"
        if errors > 0:
            result += f"\n⚠️ Ошибок: {errors}"

        await message.answer(result)

    except Exception as e:
        logger.error("Error in test_check_expiring: %s", e)
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.message()
async def message_handler(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n\n"
        "Используйте /start для навигации",
        reply_markup=get_menu_keyboard(),
    )
