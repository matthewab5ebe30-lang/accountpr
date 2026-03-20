from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

from config import Config
from database import Database
from keyboards.inline import group_subscribe_keyboard
from services.anti_spam import AntiSpamService
from services.subscription import is_user_subscribed


router = Router()


def build_group_subscription_text(full_name: str) -> str:
    return (
        "<b>ANDERSON ONE | COMMUNITY</b>\n\n"
        f"{full_name}, чтобы писать в этом чате, подтвердите доступ через кнопки ниже.\n\n"
        "После вступления нажмите кнопку подтверждения, и сообщение бота исчезнет.\n\n"
        "<b>Разработчик бота:</b> @andreuanderson"
    )


def _is_community_chat(message: Message, config: Config) -> bool:
    if message.chat.username:
        username = f"@{message.chat.username.lower()}"
        known_usernames = {
            value["chat_id"].lower()
            for value in config.community_chats.values()
            if value["chat_id"].startswith("@")
        }
        if username in known_usernames:
            return True

    return message.chat.id in config.community_chat_id_whitelist


async def _delete_previous_warning(
    bot: Bot,
    anti_spam: AntiSpamService,
    chat_id: int,
    user_id: int,
) -> None:
    warning_message_id = anti_spam.pop_warning_message(chat_id, user_id)
    if not warning_message_id:
        return

    try:
        await bot.delete_message(chat_id=chat_id, message_id=warning_message_id)
    except Exception:
        pass


@router.callback_query(F.data == "group_check_subscription")
async def group_check_subscription(
    callback: CallbackQuery,
    bot: Bot,
    config: Config,
    anti_spam: AntiSpamService,
) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    subscribed = await is_user_subscribed(bot, callback.from_user.id, config.main_channel_id)
    if not subscribed:
        await callback.answer("Подписка пока не подтверждена", show_alert=True)
        return

    anti_spam.clear_warning_message(callback.message.chat.id, callback.from_user.id)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer("Доступ подтвержден")


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def moderate_group_messages(
    message: Message,
    bot: Bot,
    db: Database,
    config: Config,
    anti_spam: AntiSpamService,
) -> None:
    if not message.from_user or message.from_user.is_bot:
        return

    if not _is_community_chat(message, config):
        return

    user_id = message.from_user.id
    await db.add_user(user_id)

    subscribed = await is_user_subscribed(bot, user_id, config.main_channel_id)
    if not subscribed:
        await _delete_previous_warning(bot, anti_spam, message.chat.id, user_id)
        try:
            await message.delete()
        except Exception:
            pass

        warning_message = await message.answer(
            build_group_subscription_text(message.from_user.full_name),
            reply_markup=group_subscribe_keyboard(config.main_channel_url),
        )
        anti_spam.set_warning_message(message.chat.id, user_id, warning_message.message_id)
        return

    await _delete_previous_warning(bot, anti_spam, message.chat.id, user_id)

    if not anti_spam.allow_message(
        user_id,
        config.max_posts_per_minute,
        config.post_cooldown_seconds,
    ):
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer(
            f"Писать можно не чаще одного сообщения в {config.post_cooldown_seconds} сек."
        )
        return

    content_text = (message.text or message.caption or "").strip()
    if not content_text:
        return

    if anti_spam.contains_link(content_text):
        joined_date = await db.get_user_joined_date(user_id)
        if anti_spam.is_new_user(joined_date, config.new_user_link_block_seconds):
            try:
                await message.delete()
            except Exception:
                pass
            await message.answer(
                "Ссылки для новых пользователей ограничены в течение 1 минуты после первого входа в бота."
            )
            return

    if anti_spam.contains_prohibited_content(content_text):
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer("Сообщение удалено: обнаружена токсичная или опасная лексика.")
        return

    if config.blacklist_words and anti_spam.contains_blacklisted_word(content_text, config.blacklist_words):
        try:
            await message.delete()
        except Exception:
            pass
        await message.answer("Сообщение удалено: найдено запрещенное слово.")
