"""Logging configuration using loguru.

The log file is written to ``data/oshpoint.log``.  Logs are rotated
when they reach 10 MB and kept for 10 days, compressed as zip.
"""

from pathlib import Path
from loguru import logger


def setup_logging() -> None:
    """Configure the loguru logger.

    This function should be called once at application startup.  It
    sets up a rotating file handler and logs that logging has been
    configured.
    """
    log_path = Path("data")
    log_path.mkdir(parents=True, exist_ok=True)
    logger.add(
        log_path / "oshpoint.log",
        rotation="10 MB",
        retention="10 days",
        compression="zip",
        enqueue=True,
    )
    logger.info("Logging configured")
