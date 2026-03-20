from __future__ import annotations

from dataclasses import dataclass, field
import os
from typing import Dict, List

from dotenv import load_dotenv


CommunityChats = Dict[str, Dict[str, str]]


def _parse_int_list(raw_value: str) -> List[int]:
    if not raw_value.strip():
        return []
    values: List[int] = []
    for item in raw_value.split(","):
        item = item.strip()
        if item and item.lstrip("-").isdigit():
            values.append(int(item))
    return values


def _parse_word_list(raw_value: str) -> List[str]:
    if not raw_value.strip():
        return []
    return [part.strip().lower() for part in raw_value.split(",") if part.strip()]


@dataclass(slots=True)
class Config:
    bot_token: str
    main_channel_id: str
    main_channel_url: str
    community_chats: CommunityChats
    community_chat_id_whitelist: List[int]
    admin_ids: List[int]
    default_price_stars: int
    stars_provider_token: str
    max_posts_per_minute: int
    post_cooldown_seconds: int
    new_user_link_block_seconds: int
    blacklist_words: List[str] = field(default_factory=list)
    pin_duration_seconds: int = 600
    sqlite_path: str = "community_bot.db"


def load_config() -> Config:
    load_dotenv()

    community_chats: CommunityChats = {
        "jobs": {
            "title": "💼 Работа | Вакансии",
            "url": "https://t.me/workhub_jobs_ru",
            "chat_id": "@workhub_jobs_ru",
        },
        "dating": {
            "title": "💘 Знакомства & Общение",
            "url": "https://t.me/workhub_dating",
            "chat_id": "@workhub_dating",
        },
        "housing": {
            "title": "🔄 Взаимные подписки",
            "url": "https://t.me/workhub_referrals",
            "chat_id": "@workhub_referrals",
        },
        "general": {
            "title": "💬 Общение 24/7",
            "url": "https://t.me/workhub_chatru",
            "chat_id": "@workhub_chatru",
        },
        "referrals": {
            "title": "🤝 Заработок онлайн Рефераллы",
            "url": "https://t.me/workhub_referrals_ru",
            "chat_id": "@workhub_referrals_ru",
        },
    }

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("Не задан BOT_TOKEN в переменных окружения.")

    return Config(
        bot_token=bot_token,
        main_channel_id=os.getenv("MAIN_CHANNEL_ID", "@anderson_one_life").strip(),
        main_channel_url=os.getenv("MAIN_CHANNEL_URL", "https://t.me/anderson_one_life").strip(),
        community_chats=community_chats,
        community_chat_id_whitelist=_parse_int_list(os.getenv("COMMUNITY_CHAT_IDS", "")),
        admin_ids=_parse_int_list(os.getenv("ADMIN_IDS", "")),
        default_price_stars=max(1, int(os.getenv("DEFAULT_PRICE_STARS", "30"))),
        stars_provider_token=os.getenv("STARS_PROVIDER_TOKEN", "").strip(),
        max_posts_per_minute=max(1, int(os.getenv("MAX_POSTS_PER_MINUTE", "60"))),
        post_cooldown_seconds=max(0, int(os.getenv("POST_COOLDOWN_SECONDS", "1"))),
        new_user_link_block_seconds=max(
            0,
            int(
                os.getenv(
                    "NEW_USER_LINK_BLOCK_SECONDS",
                    os.getenv("NEW_USER_DAYS_LINK_BLOCK", "60"),
                )
            ),
        ),
        blacklist_words=_parse_word_list(os.getenv("BLACKLIST_WORDS", "")),
        pin_duration_seconds=max(0, int(os.getenv("PIN_DURATION_SECONDS", "600"))),
        sqlite_path=os.getenv("SQLITE_PATH", "community_bot.db").strip() or "community_bot.db",
    )
