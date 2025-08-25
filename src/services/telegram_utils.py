from __future__ import annotations

import re
from typing import Optional, Union


def normalize_chat_id(raw: Optional[str]) -> Union[int, str, None]:
    """
    Приводит настройку канала к виду, который принимает Telegram API:
    - '@username' -> '@username'
    - 'username'  -> '@username'
    - 'https://t.me/username' -> '@username'
    - '-1001234567890' -> int(-1001234567890)
    Возвращает int | str | None.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None

    # t.me/username
    m = re.search(r"(?:https?://)?t\.me/([^/?#]+)", s, flags=re.IGNORECASE)
    if m:
        username = m.group(1).lstrip("@")
        return f"@{username}"

    # @username
    if s.startswith("@"):
        return s

    # числовой id (включая -100...)
    try:
        return int(s)
    except ValueError:
        pass

    # просто имя без @
    return f"@{s.lstrip('@')}"
