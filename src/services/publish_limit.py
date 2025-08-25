from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..db.repo import Repository


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PublishDecision:
    allowed: bool
    next_time: datetime | None  # когда снова можно публиковать (для weekly/quota исчерпано)


class PublishLimiter:
    """
    Политика:
    - weekly (реализуем как quota_total=1 на 7 дней): 1 объявление каждые 7 дней.
    - quota (N / 30 дней): без ожидания между публикациями, пока есть остаток.
    - unlimited (30 дней): без ограничений по количеству.

    В БД это всё хранится в таблице user_limits.
    """

    def __init__(self, repo: Repository):
        self.repo = repo

    async def can_publish(self, user_id: int) -> tuple[bool, datetime | None]:
        """
        Возвращает (allowed, next_time).
        Всегда гарантирует наличие лимита (создаёт weekly, если его нет).
        """
        ul = await self.repo.get_or_create_default_limit(user_id)
        now = utcnow()

        # Если спец-лимит истёк — откат на weekly
        if ul.expires_at and ul.expires_at <= now:
            ul = await self.repo.reset_to_weekly(user_id, start_from=now)

        # unlimited: всегда можно до expires_at
        if ul.mode == "unlimited":
            return True, None

        # quota (включая weekly как частный случай):
        remaining = (ul.quota_total or 0) - (ul.quota_used or 0)

        if remaining > 0:
            # Если это именно weekly (quota_total == 1 и окно 7 дней),
            # то next_time показываем только после траты слота.
            return True, None

        # слотов нет
        return False, ul.expires_at
