from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import Config


PRIMARY_ICON = "5285430309720966085"
SUCCESS_ICON = "5310076249404621168"
NEUTRAL_ICON = "5285032475490273112"


def _success_button(text: str, **kwargs: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        style="success",
        icon_custom_emoji_id=SUCCESS_ICON,
        **kwargs,
    )


def _primary_button(text: str, **kwargs: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        style="primary",
        icon_custom_emoji_id=PRIMARY_ICON,
        **kwargs,
    )


def _neutral_button(text: str, **kwargs: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text,
        icon_custom_emoji_id=NEUTRAL_ICON,
        **kwargs,
    )


def main_menu_keyboard(config: Config) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_success_button("Основной канал", url=config.main_channel_url)],
            [
                _primary_button("Работа", callback_data="show_chat:jobs"),
                _primary_button("Знакомства", callback_data="show_chat:dating"),
            ],
            [
                _primary_button("Подписки", callback_data="show_chat:housing"),
                _primary_button("Общение", callback_data="show_chat:general"),
            ],
            [_primary_button("Рефералы", callback_data="show_chat:referrals")],
            [_success_button("Платное объявление", callback_data="paid_announcement")],
            [_neutral_button("Мои приглашения", callback_data="show_referrals")],
        ]
    )


def subscribe_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_success_button("Подписаться на канал", url=channel_url)],
            [_success_button("Я подписался", callback_data="check_subscription")],
        ]
    )


def group_subscribe_keyboard(channel_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_success_button("Основной канал", url=channel_url)],
            [_success_button("Я подписался", callback_data="group_check_subscription")],
        ]
    )


def paid_chat_keyboard(config: Config) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_primary_button(config.community_chats["jobs"]["title"], callback_data="paid_chat:jobs")],
            [_primary_button(config.community_chats["dating"]["title"], callback_data="paid_chat:dating")],
            [_primary_button(config.community_chats["housing"]["title"], callback_data="paid_chat:housing")],
            [_primary_button(config.community_chats["general"]["title"], callback_data="paid_chat:general")],
            [_primary_button(config.community_chats["referrals"]["title"], callback_data="paid_chat:referrals")],
            [_neutral_button("Назад", callback_data="open_menu")],
        ]
    )


def chat_card_keyboard(config: Config, chat_key: str) -> InlineKeyboardMarkup:
    chat = config.community_chats[chat_key]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_success_button("Перейти в чат", url=chat["url"])],
            [_success_button("Разместить объявление", callback_data=f"paid_chat_direct:{chat_key}")],
            [_neutral_button("Назад в меню", callback_data="open_menu")],
        ]
    )


def referrals_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [_neutral_button("Назад в меню", callback_data="open_menu")],
        ]
    )
