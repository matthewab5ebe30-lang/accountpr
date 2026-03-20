from __future__ import annotations

import re
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque, DefaultDict, Iterable, Optional


LINK_REGEX = re.compile(r"(https?://|t\\.me/|www\\.)", re.IGNORECASE)

PROHIBITED_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\\bуб(ей|ить|ью|ьем|ьют)\\b",
        r"\\b(зареж|повесь|сожг|взорв|избей|уничтож)\\w*",
        r"\\b(террор|экстрем|геноцид|наци|фашист|расист)\\w*",
        r"\\b(ненавиж|выгнат|истреб|ликвидир)\\w*",
        r"\\b(мраз|твар|скотин)\\w*",
        r"\\b(пидор|пидр|хач|чурк|ниггер)\\w*",
    ]
]


class AntiSpamService:
    def __init__(self) -> None:
        self._history: DefaultDict[int, Deque[datetime]] = defaultdict(deque)
        self._warning_messages: dict[tuple[int, int], int] = {}

    def allow_message(self, user_id: int, max_posts_per_minute: int, cooldown_seconds: int) -> bool:
        now = datetime.now(timezone.utc)
        border = now - timedelta(minutes=1)
        user_queue = self._history[user_id]

        while user_queue and user_queue[0] < border:
            user_queue.popleft()

        if cooldown_seconds > 0 and user_queue:
            if now - user_queue[-1] < timedelta(seconds=cooldown_seconds):
                return False

        if len(user_queue) >= max_posts_per_minute:
            return False

        user_queue.append(now)
        return True

    @staticmethod
    def contains_link(text: str) -> bool:
        return bool(LINK_REGEX.search(text or ""))

    @staticmethod
    def contains_blacklisted_word(text: str, blacklist_words: Iterable[str]) -> bool:
        lowered = (text or "").lower()
        return any(word in lowered for word in blacklist_words)

    @staticmethod
    def contains_prohibited_content(text: str) -> bool:
        content = text or ""
        return any(pattern.search(content) for pattern in PROHIBITED_PATTERNS)

    @staticmethod
    def is_new_user(joined_date_iso: Optional[str], seconds_threshold: int) -> bool:
        if seconds_threshold <= 0:
            return False
        if not joined_date_iso:
            return True
        try:
            joined_date = datetime.fromisoformat(joined_date_iso)
        except ValueError:
            return True

        if joined_date.tzinfo is None:
            joined_date = joined_date.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) - joined_date < timedelta(seconds=seconds_threshold)

    def set_warning_message(self, chat_id: int, user_id: int, message_id: int) -> None:
        self._warning_messages[(chat_id, user_id)] = message_id

    def pop_warning_message(self, chat_id: int, user_id: int) -> Optional[int]:
        return self._warning_messages.pop((chat_id, user_id), None)

    def clear_warning_message(self, chat_id: int, user_id: int) -> None:
        self._warning_messages.pop((chat_id, user_id), None)
