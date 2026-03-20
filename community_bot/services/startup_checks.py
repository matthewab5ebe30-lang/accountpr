from __future__ import annotations

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest

from config import Config


ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


async def validate_bot_access(bot: Bot, config: Config) -> list[str]:
    me = await bot.get_me()
    report: list[str] = []

    try:
        await bot.get_chat(config.main_channel_id)
        main_member = await bot.get_chat_member(config.main_channel_id, me.id)
    except TelegramBadRequest as exc:
        raise RuntimeError(
            "Бот не может проверить подписку на основной канал. "
            "Добавьте бота администратором в основной канал и включите ему доступ к участникам."
        ) from exc

    if main_member.status not in ADMIN_STATUSES:
        raise RuntimeError(
            "Для проверки подписки бот должен быть администратором основного канала."
        )

    report.append("Основной канал: доступ к проверке подписки подтвержден.")

    for chat in config.community_chats.values():
        member = await bot.get_chat_member(chat["chat_id"], me.id)
        if member.status not in ADMIN_STATUSES:
            raise RuntimeError(
                f"Бот должен быть администратором в чате {chat['title']} ({chat['chat_id']})."
            )

        capabilities = []
        if getattr(member, "can_delete_messages", False):
            capabilities.append("delete")
        if getattr(member, "can_pin_messages", False):
            capabilities.append("pin")
        if getattr(member, "can_restrict_members", False):
            capabilities.append("restrict")

        report.append(
            f"{chat['title']}: права подтверждены"
            + (f" ({', '.join(capabilities)})" if capabilities else "")
            + "."
        )

    return report