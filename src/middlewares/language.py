from __future__ import annotations

from typing import Any, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from ..db.repo import Repository
from ..services.i18n import I18n
from ..config import Settings


class LanguageMiddleware(BaseMiddleware):
    """
    Прокидывает в хендлеры:
      - t: Callable[[key], str]
      - i18n: I18n
      - repo: Repository
      - settings: Settings
    """

    def __init__(self, repo: Repository, i18n: I18n, default_lang: str = "ru", settings: Settings | None = None) -> None:
        super().__init__()
        self.repo = repo
        self.i18n = i18n
        self.default_lang = (default_lang or "ru").lower()
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Any],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user = None
        if isinstance(event, Message):
            tg_user = event.from_user
        elif isinstance(event, CallbackQuery):
            tg_user = event.from_user
        else:
            tg_user = getattr(event, "from_user", None)

        lang = self.default_lang

        if tg_user is not None:
            try:
                db_user = await self.repo.create_or_get_user(
                    telegram_id=tg_user.id,
                    username=tg_user.username,
                    first_name=getattr(tg_user, "first_name", None),
                    last_name=getattr(tg_user, "last_name", None),
                )
                if getattr(db_user, "lang", None):
                    lang = db_user.lang
            except Exception:
                pass

        t = self.i18n.get_translator(lang)

        data["t"] = t
        data["i18n"] = self.i18n
        data["repo"] = self.repo
        data["settings"] = self.settings  # ← теперь хендлеры могут принимать settings

        return await handler(event, data)
