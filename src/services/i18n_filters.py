from __future__ import annotations

import re
import unicodedata
from typing import Iterable
from aiogram.filters import BaseFilter
from aiogram.types import Message


def _strip_emoji(s: str) -> str:
    # удаляем все символы из категории "прочие символы" (So) и смайлики
    return "".join(
        ch for ch in s
        if unicodedata.category(ch) != "So" and not (0x1F300 <= ord(ch) <= 0x1FAFF)
    )


def _normalize(s: str) -> str:
    # NFKC, убрать эмодзи, схлопнуть пробелы, нижний регистр
    s = unicodedata.normalize("NFKC", s or "")
    s = _strip_emoji(s)
    s = re.sub(r"\s+", " ", s, flags=re.M).strip()
    s = s.casefold()
    # оставим только буквы/цифры/базовые знаки — чтобы «:», «!» и т.п. не мешали
    s = "".join(ch for ch in s if ch.isalnum() or ch in " +-_/().,")
    return s


# Небольшие безопасные синонимы (на случай изменений в YAML/опечаток)
_ALIASES: dict[str, set[str]] = {
    "btn_create_ad": {
        "создать объявление", "жарыя түзүү", "жария түзүү",
    },
    "btn_language": {"язык", "тил"},
    "btn_my_ads": {"мои объявления", "менин жарнамаларым"},
    "btn_payments": {"платежи", "төлөмдөр"},
    "btn_profile": {"личный профиль", "жеке профиль"},
    "back": {"назад", "артка", "менюга кайтуу"},
}


class TextKey(BaseFilter):
    """
    Сравнивает текст сообщения с переводом по ключу i18n, но «умно»:
    - игнорирует эмодзи и пунктуацию;
    - не чувствителен к регистру;
    - схлопывает лишние пробелы;
    - поддерживает небольшие синонимы в _ALIASES.
    """
    def __init__(self, key: str):
        self.key = key

    async def __call__(self, event: Message, t) -> bool:
        if not event or not (event.text or "").strip():
            return False

        src = _normalize(event.text)
        want = _normalize(t(self.key))

        if src == want:
            return True

        # попробуем без эмодзи/пунктуации, уже нормализовано выше;
        # плюс синонимы на всякий
        aliases: Iterable[str] = _ALIASES.get(self.key, set())
        if aliases and src in {_normalize(a) for a in aliases}:
            return True

        return False
