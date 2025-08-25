from __future__ import annotations

from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import Settings
from .services.i18n import I18n
from .middlewares.language import LanguageMiddleware
from .db import base as db_base
from .db.repo import Repository


def create_bot(settings: Settings):
    db_base.init_engine(settings.database_url)
    repo = Repository(db_base.session_maker)

    locales_dir = Path(__file__).resolve().parent / "texts"
    i18n = I18n(locales_dir=locales_dir, default_lang=getattr(settings, "default_lang", "ru"))

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # ← сюда добавили settings
    dp.update.middleware(LanguageMiddleware(repo, i18n, getattr(settings, "default_lang", "ru"), settings))

    return bot, dp, repo
