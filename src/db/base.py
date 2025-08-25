# src/db/base.py
from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase


# Базовый класс для моделей (alembic импортирует Base.metadata)
class Base(DeclarativeBase):
    pass


# Глобальные объекты движка и фабрики сессий
engine: Optional[AsyncEngine] = None
session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def init_engine(database_url: str, echo: bool = False) -> None:
    """
    Инициализирует AsyncEngine и async_sessionmaker.
    Вызывается один раз при старте бота.
    """
    global engine, session_maker
    engine = create_async_engine(database_url, echo=echo, future=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)


def get_engine() -> AsyncEngine:
    if engine is None:
        raise RuntimeError("DB engine is not initialized. Call init_engine(...) first.")
    return engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if session_maker is None:
        raise RuntimeError("Session maker is not initialized. Call init_engine(...) first.")
    return session_maker
