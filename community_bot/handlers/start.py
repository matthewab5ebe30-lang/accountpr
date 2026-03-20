from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from config import Config
from database import Database
from keyboards.inline import chat_card_keyboard, main_menu_keyboard, referrals_keyboard, subscribe_keyboard
from services.subscription import is_user_subscribed


router = Router()


SUBSCRIPTION_REQUIRED_TEXT = (
    "Нужно подписаться на основной канал, прежде чем писать в чатах сообщества."
)

CHAT_DESCRIPTIONS = {
    "jobs": "Вакансии, подработки, поиск сотрудников и деловые контакты.",
    "dating": "Знакомства, новые люди, общение и поиск пары.",
    "housing": "Взаимные подписки, обмен активностью и быстрый нетворкинг.",
    "general": "Живой чат 24/7: общение, обсуждения и знакомства по интересам.",
    "referrals": "Реферальные офферы, заработок онлайн и полезные связки.",
}


def build_welcome_text(config: Config) -> str:
    chats = config.community_chats
    return (
        "<b>ANDERSON ONE | COMMUNITY HUB</b>\n\n"
        "<i>Единая точка входа в комьюнити: чаты, объявления, рефералы и быстрый доступ ко всем разделам.</i>\n\n"
        "<b>Доступные разделы:</b>\n"
        f"• {chats['jobs']['title']}\n"
        f"• {chats['dating']['title']}\n"
        f"• {chats['housing']['title']}\n"
        f"• {chats['general']['title']}\n"
        f"• {chats['referrals']['title']}\n\n"
        "<b>Как это работает:</b>\n"
        "• писать в чатах можно только после подписки\n"
        "• платные объявления публикуются за Stars\n"
        "• быстрый вход в каждый чат доступен по кнопкам ниже\n\n"
        f"<b>Основной канал:</b>\n{config.main_channel_url}\n\n"
        "<b>Разработчик бота:</b> @andreuanderson"
    )


def build_chat_card_text(config: Config, chat_key: str) -> str:
    chat = config.community_chats[chat_key]
    return (
        f"<b>Раздел {chat['title']}</b>\n\n"
        f"{CHAT_DESCRIPTIONS[chat_key]}\n\n"
        "<b>Что можно делать:</b>\n"
        "• общаться и публиковать сообщения после подписки\n"
        "• быстро перейти в чат по кнопке ниже\n"
        "• разместить платное объявление за Stars\n\n"
        f"<b>Ссылка:</b>\n{chat['url']}\n\n"
        "<b>Разработчик бота:</b> @andreuanderson"
    )


def build_referrals_text(config: Config, bot_username: str | None, user_id: int, invited_count: int, leaderboard: list[tuple[int, int]]) -> str:
    referral_link = (
        f"https://t.me/{bot_username}?start={user_id}" if bot_username else "У бота пока нет username для реферальной ссылки."
    )
    top_lines = []
    for index, (leader_user_id, count) in enumerate(leaderboard[:5], start=1):
        top_lines.append(f"{index}. <a href='tg://user?id={leader_user_id}'>Пользователь {leader_user_id}</a> — {count}")
    top_text = "\n".join(top_lines) if top_lines else "Пока нет приглашений в рейтинге."

    return (
        "<b>ANDERSON ONE | REFERRALS</b>\n\n"
        f"<b>Приглашено пользователей:</b> {invited_count}\n"
        f"<b>Ваша ссылка:</b>\n{referral_link}\n\n"
        f"<b>Топ рефереров:</b>\n{top_text}\n\n"
        "<b>Разработчик бота:</b> @andreuanderson"
    )


def _parse_referrer(command: CommandObject | None, user_id: int) -> int | None:
    if not command or not command.args:
        return None
    arg = command.args.strip()
    if not arg.isdigit():
        return None
    referrer_id = int(arg)
    if referrer_id == user_id:
        return None
    return referrer_id


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    bot: Bot,
    db: Database,
    config: Config,
) -> None:
    if not message.from_user:
        return

    user_id = message.from_user.id
    referrer_id = _parse_referrer(command, user_id)
    await db.add_user(telegram_id=user_id, referrer_id=referrer_id)

    subscribed = await is_user_subscribed(bot, user_id, config.main_channel_id)
    if not subscribed:
        await message.answer(
            SUBSCRIPTION_REQUIRED_TEXT,
            reply_markup=subscribe_keyboard(config.main_channel_url),
        )
        return

    await message.answer(build_welcome_text(config), reply_markup=main_menu_keyboard(config))


@router.callback_query(F.data == "check_subscription")
async def check_subscription(callback: CallbackQuery, bot: Bot, config: Config) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    subscribed = await is_user_subscribed(bot, callback.from_user.id, config.main_channel_id)
    if not subscribed:
        await callback.answer("Подписка пока не найдена", show_alert=True)
        return

    await callback.message.edit_text(build_welcome_text(config), reply_markup=main_menu_keyboard(config))
    await callback.answer("Подписка подтверждена")


@router.callback_query(F.data == "open_menu")
async def open_menu(callback: CallbackQuery, bot: Bot, config: Config) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    subscribed = await is_user_subscribed(bot, callback.from_user.id, config.main_channel_id)
    if not subscribed:
        await callback.message.edit_text(
            SUBSCRIPTION_REQUIRED_TEXT,
            reply_markup=subscribe_keyboard(config.main_channel_url),
        )
        await callback.answer()
        return

    await callback.message.edit_text(build_welcome_text(config), reply_markup=main_menu_keyboard(config))
    await callback.answer()


@router.callback_query(F.data.startswith("show_chat:"))
async def show_chat_card(callback: CallbackQuery, bot: Bot, config: Config) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    subscribed = await is_user_subscribed(bot, callback.from_user.id, config.main_channel_id)
    if not subscribed:
        await callback.message.edit_text(
            SUBSCRIPTION_REQUIRED_TEXT,
            reply_markup=subscribe_keyboard(config.main_channel_url),
        )
        await callback.answer()
        return

    _, chat_key = callback.data.split(":", maxsplit=1)
    if chat_key not in config.community_chats:
        await callback.answer("Чат не найден", show_alert=True)
        return

    await callback.message.edit_text(
        build_chat_card_text(config, chat_key),
        reply_markup=chat_card_keyboard(config, chat_key),
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data == "show_referrals")
async def show_referrals(callback: CallbackQuery, bot: Bot, db: Database, config: Config) -> None:
    if not callback.from_user or not callback.message:
        await callback.answer()
        return

    subscribed = await is_user_subscribed(bot, callback.from_user.id, config.main_channel_id)
    if not subscribed:
        await callback.message.edit_text(
            SUBSCRIPTION_REQUIRED_TEXT,
            reply_markup=subscribe_keyboard(config.main_channel_url),
        )
        await callback.answer()
        return

    me = await bot.get_me()
    invited_count = await db.get_referral_count(callback.from_user.id)
    leaderboard = await db.get_top_referrers(limit=5)

    await callback.message.edit_text(
        build_referrals_text(config, me.username, callback.from_user.id, invited_count, leaderboard),
        reply_markup=referrals_keyboard(),
        disable_web_page_preview=True,
    )
    await callback.answer()
