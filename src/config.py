from __future__ import annotations

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # токен и админ
    bot_token: str = Field(...)
    admin_id: int = Field(...)

    # БД
    database_url: str = Field(default="sqlite+aiosqlite:///data/oshpoint.db")

    # язык по умолчанию
    default_lang: str = Field(default="ru")

    # публикация объявлений (чат и, при необходимости, топик форума)
    bike_channel: Optional[str] = Field(default=None)
    bike_topic_id: Optional[int] = Field(default=None)

    # общий чат/группа (например, для ссылок/сообщений в /start)
    general_chat: Optional[str] = Field(default=None)
    general_topic_id: Optional[int] = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("admin_id", mode="before")
    @classmethod
    def _cast_admin_id(cls, v):
        return int(v) if v not in (None, "", "None") else 0

    @field_validator("bike_topic_id", "general_topic_id", mode="before")
    @classmethod
    def _cast_topic(cls, v):
        if v in (None, "", "None", "null"):
            return None
        return int(v)

    @field_validator("default_lang", mode="before")
    @classmethod
    def _norm_lang(cls, v):
        if not v:
            return "ru"
        s = str(v).lower()
        return "ky" if s.startswith("ky") else "ru"


























































# """Configuration loading via pydantic and dotenv.

# This module defines the :class:`Settings` class, which reads
# configuration values from environment variables.  Values can be
# specified in a `.env` file at the project root.  Use the `.env.example`
# template as a starting point.
# """

# from __future__ import annotations

# from pathlib import Path
# from typing import Optional
# from pydantic import Field, field_validator
# from dotenv import load_dotenv
# from pydantic_settings import BaseSettings, SettingsConfigDict


# # Load environment variables from a .env file if present.  We call this
# # at module import time so that other modules which instantiate
# # :class:`Settings` will see the loaded variables.
# load_dotenv()

# class Settings(BaseSettings):
#     bot_token: str = Field(..., env="BOT_TOKEN")
#     admin_id: int = Field(..., env="ADMIN_ID")
#     bike_channel: str = Field(..., env="BIKE_CHANNEL")
#     general_chat: str = Field(..., env="GENERAL_CHAT")
#     base_post_limit_per_7days: int = Field(1, env="BASE_POST_LIMIT_PER_7DAYS")
#     default_lang: str = Field("ru", env="DEFAULT_LANG")
#     database_url: str = Field(..., env="DATABASE_URL")

#     model_config = SettingsConfigDict(
#         env_file=".env",
#         env_file_encoding="utf-8",
#     )

#     @field_validator("default_lang")
#     @classmethod
#     def validate_default_lang(cls, v: str) -> str:
#         if v not in {"ru", "ky"}:
#             raise ValueError("DEFAULT_LANG must be 'ru' or 'ky'")
#         return v



