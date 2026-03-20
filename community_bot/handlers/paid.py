from __future__ import annotations

from uuid import uuid4

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from config import Config
from database import Database
from keyboards.inline import paid_chat_keyboard, subscribe_keyboard
from services.payment import format_paid_announcement, schedule_unpin
from services.subscription import is_user_subscribed
from states.paid import PaidAnnouncementState


router = Router()


@router.callback_query(F.data == "paid_announcement")
async def paid_announcement_entry(
    callback: CallbackQuery,
    state: FSMContext,
    config: Config,
    bot: Bot,
) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    subscribed = await is_user_subscribed(bot, callback.from_user.id, config.main_channel_id)
    if not subscribed:
        await callback.message.edit_text(
            "Нужно подписаться на основной канал, прежде чем пользоваться этой функцией.",
            reply_markup=subscribe_keyboard(config.main_channel_url),
        )
        await callback.answer()
        return

    await state.set_state(PaidAnnouncementState.choose_chat)
    await callback.message.edit_text(
        "Выберите чат, где хотите опубликовать платное объявление.",
        reply_markup=paid_chat_keyboard(config),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("paid_chat_direct:"))
async def paid_announcement_entry_direct(
    callback: CallbackQuery,
    state: FSMContext,
    config: Config,
    bot: Bot,
) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    subscribed = await is_user_subscribed(bot, callback.from_user.id, config.main_channel_id)
    if not subscribed:
        await callback.message.edit_text(
            "Нужно подписаться на основной канал, прежде чем пользоваться этой функцией.",
            reply_markup=subscribe_keyboard(config.main_channel_url),
        )
        await callback.answer()
        return

    _, chat_key = callback.data.split(":", maxsplit=1)
    if chat_key not in config.community_chats:
        await callback.answer("Чат не найден", show_alert=True)
        return

    await state.update_data(chat_key=chat_key)
    await state.set_state(PaidAnnouncementState.waiting_text)
    await callback.message.edit_text(
        f"<b>{config.community_chats[chat_key]['title']}</b>\n\n"
        "Отправьте текст объявления одним сообщением.\n"
        "После этого бот пришлет счет на оплату в Telegram Stars.",
    )
    await callback.answer()


@router.callback_query(PaidAnnouncementState.choose_chat, F.data.startswith("paid_chat:"))
async def paid_announcement_select_chat(
    callback: CallbackQuery,
    state: FSMContext,
    config: Config,
) -> None:
    if not callback.message:
        await callback.answer()
        return

    _, chat_key = callback.data.split(":", maxsplit=1)
    if chat_key not in config.community_chats:
        await callback.answer("Чат не найден", show_alert=True)
        return

    await state.update_data(chat_key=chat_key)
    await state.set_state(PaidAnnouncementState.waiting_text)

    await callback.message.edit_text(
        "<b>Выбор чата подтвержден</b>\n\n"
        "Отправьте текст объявления одним сообщением.\n"
        "После этого бот пришлет счет на оплату в Telegram Stars.",
    )
    await callback.answer()


@router.message(PaidAnnouncementState.waiting_text, Command("cancel"))
@router.message(PaidAnnouncementState.waiting_payment, Command("cancel"))
async def cancel_paid_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Операция отменена. Нажмите /start чтобы вернуться в меню.")


@router.message(PaidAnnouncementState.waiting_text)
async def paid_announcement_receive_text(
    message: Message,
    state: FSMContext,
    db: Database,
    config: Config,
) -> None:
    if not message.from_user:
        return

    announcement_text = (message.text or message.caption or "").strip()
    if not announcement_text:
        await message.answer("Нужен текст объявления. Отправьте обычное текстовое сообщение.")
        return

    data = await state.get_data()
    chat_key = data.get("chat_key")
    if not chat_key or chat_key not in config.community_chats:
        await state.clear()
        await message.answer("Не удалось определить чат. Начните заново: /start")
        return

    price_stars = await db.get_price_stars(config.default_price_stars)
    payload = f"paid:{chat_key}:{uuid4().hex}"

    await state.update_data(announcement_text=announcement_text, payload=payload, price_stars=price_stars)
    await state.set_state(PaidAnnouncementState.waiting_payment)

    await message.answer_invoice(
        title="Платное объявление",
        description=(
            f"Публикация в чате {config.community_chats[chat_key]['title']} | "
            f"Разработчик: @andreuanderson"
        ),
        payload=payload,
        provider_token=config.stars_provider_token,
        currency="XTR",
        prices=[LabeledPrice(label="Размещение объявления", amount=price_stars)],
    )


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery) -> None:
    if pre_checkout_query.invoice_payload.startswith("paid:"):
        await pre_checkout_query.answer(ok=True)
    else:
        await pre_checkout_query.answer(ok=False, error_message="Неизвестный тип платежа")


@router.message(PaidAnnouncementState.waiting_payment, F.successful_payment)
async def process_successful_payment(
    message: Message,
    state: FSMContext,
    bot: Bot,
    db: Database,
    config: Config,
) -> None:
    if not message.from_user or not message.successful_payment:
        return

    data = await state.get_data()
    chat_key = data.get("chat_key")
    announcement_text = data.get("announcement_text", "")

    if not chat_key or chat_key not in config.community_chats or not announcement_text:
        await state.clear()
        await message.answer("Оплата получена, но данные объявления не найдены. Обратитесь к администратору.")
        return

    chat_info = config.community_chats[chat_key]
    final_text = format_paid_announcement(announcement_text, config.main_channel_url)

    posted_message = await bot.send_message(
        chat_id=chat_info["chat_id"],
        text=final_text,
        disable_web_page_preview=True,
    )

    if config.pin_duration_seconds > 0:
        try:
            await bot.pin_chat_message(
                chat_id=chat_info["chat_id"],
                message_id=posted_message.message_id,
                disable_notification=True,
            )
            schedule_unpin(
                bot,
                chat_id=chat_info["chat_id"],
                message_id=posted_message.message_id,
                delay_seconds=config.pin_duration_seconds,
            )
        except Exception:
            # Если в чате нет прав на pin, публикация все равно уже отправлена.
            pass

    await db.save_payment(
        user_id=message.from_user.id,
        amount=message.successful_payment.total_amount,
        chat=chat_info["chat_id"],
    )

    await state.clear()
    await message.answer("Оплата успешна! Объявление опубликовано.")
