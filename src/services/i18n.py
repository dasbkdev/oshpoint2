from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, Any
import yaml


class I18n:
    """
    Простой YAML-i18n.
    - грузит все *.yml из каталога локалей;
    - t(lang, key, **kwargs) -> строка (fallback на default_lang, затем на key);
    - translator(lang) возвращает функцию t(key, **kwargs).
    """

    def __init__(self, locales_dir: str | Path, default_lang: str = "ru") -> None:
        self.locales_dir = Path(locales_dir)
        self.default_lang = (default_lang or "ru").lower()
        self._dicts: Dict[str, Dict[str, str]] = {}
        self._load_all()

    # ---------- load/reload ----------
    def _load_all(self) -> None:
        self._dicts.clear()
        for p in self.locales_dir.glob("*.yml"):
            lang = p.stem.lower()
            with p.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            self._dicts[lang] = {str(k): str(v) for k, v in data.items()}

    def reload(self) -> None:
        self._load_all()

    # ---------- translate ------------
    def t(self, lang: str | None, key: str, **kwargs: Any) -> str:
        lang = (lang or self.default_lang).lower()
        text = (
            self._dicts.get(lang, {}).get(key)
            or self._dicts.get(self.default_lang, {}).get(key)
            or key
        )
        try:
            return text.format(**kwargs)
        except Exception:
            return text

    def translator(self, lang: str | None) -> Callable[[str], str]:
        return lambda key, **kw: self.t(lang, key, **kw)

    def get_translator(self, lang: str | None) -> Callable[[str], str]:
        return self.translator(lang)

    def __call__(self, lang: str | None) -> Callable[[str], str]:
        return self.translator(lang)

    # ---------- misc -----------------
    @property
    def langs(self) -> list[str]:
        return sorted(self._dicts.keys())
