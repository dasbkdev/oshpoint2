# src/main.py
from __future__ import annotations

import asyncio
from loguru import logger

from .logging_conf import setup_logging
from .config import Settings
from .bot_factory import create_bot
from .handlers import (
    common_router,
    create_ad_router,
    my_ads_router,
    payments_router,
    admin_router,
    admin_payments_router,
)


async def main() -> None:
    setup_logging()
    logger.info("Starting oshpoint bot")

    settings = Settings()
    bot, dp, repo = create_bot(settings)

    # Подключаем роутеры (порядок: пользовательские -> админские)
    dp.include_router(common_router)
    dp.include_router(create_ad_router)
    dp.include_router(my_ads_router)
    dp.include_router(payments_router)
    dp.include_router(admin_router)
    dp.include_router(admin_payments_router)

    # Инициализация дефолтных настроек/правил и проч.
    try:
        await repo.init_default_settings()
    except Exception as e:
        logger.warning(f"init_default_settings skipped or failed: {e}")

    # Запуск поллинга
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
