from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from config import Config
from database import Database
from keyboards.inline import subscribe_keyboard
from services.subscription import is_user_subscribed


router = Router()


def _format_top_referrers(rows: list[tuple[int, int]]) -> str:
    if not rows:
        return "Пока нет приглашений."

    lines = ["<b>Топ рефереров:</b>"]
    for idx, (user_id, count) in enumerate(rows, start=1):
        lines.append(f"{idx}. <a href='tg://user?id={user_id}'>Пользователь {user_id}</a> — {count}")
    return "\n".join(lines)


@router.message(Command("referrals"))
async def cmd_referrals(message: Message, db: Database, bot: Bot, config: Config) -> None:
    if not message.from_user:
        return

    user_id = message.from_user.id
    subscribed = await is_user_subscribed(bot, user_id, config.main_channel_id)
    if not subscribed:
        await message.answer(
            "Сначала подпишитесь на основной канал, чтобы пользоваться ботом.",
            reply_markup=subscribe_keyboard(config.main_channel_url),
        )
        return

    me = await bot.get_me()

    invited_count = await db.get_referral_count(user_id)
    leaderboard = await db.get_top_referrers(limit=10)

    referral_link = (
        f"https://t.me/{me.username}?start={user_id}" if me.username else "У бота нет username для deep-link."
    )

    text = (
        f"<b>Ваши рефералы:</b> {invited_count}\n"
        f"<b>Ваша ссылка:</b>\n{referral_link}\n\n"
        f"{_format_top_referrers(leaderboard)}"
    )

    await message.answer(text, disable_web_page_preview=True)
