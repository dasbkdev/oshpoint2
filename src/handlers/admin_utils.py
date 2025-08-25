from __future__ import annotations

from aiogram import Router, F
from aiogram.types import Message
from ..config import Settings

router = Router()

@router.message(F.text.regexp(r"^/cid(\s+.+)?$"))
async def cmd_cid(message: Message, settings: Settings):
    """
    /cid            -> вернёт ID текущего чата и, если есть, ID топика
    /cid @username  -> вернёт ID публичного канала/группы по username
    /cid -100123... -> вернёт ID, если передали численный ID
    """
    if message.from_user.id != settings.admin_id:
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 1:
        thread_id = getattr(message, "message_thread_id", None)
        text = (
            f"<b>Текущий чат</b>\n"
            f"Title: {message.chat.title}\n"
            f"ID: <code>{message.chat.id}</code>"
        )
        if thread_id:
            text += f"\nTopic (message_thread_id): <code>{thread_id}</code>"
        await message.answer(text, parse_mode="HTML")
        return

    target = parts[1].strip()
    try:
        chat = await message.bot.get_chat(target)
        title = chat.title or f"@{chat.username}" if chat.username else str(chat.id)
        await message.answer(
            f"<b>{title}</b>\nID: <code>{chat.id}</code>",
            parse_mode="HTML",
        )
    except Exception as e:
        await message.answer(f"Не удалось получить чат: {e}")
