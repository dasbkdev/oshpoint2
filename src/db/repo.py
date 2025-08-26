# src/db/repo.py
from __future__ import annotations

from typing import List, Optional, Tuple

from datetime import datetime, timedelta, timezone
import sqlalchemy as sa
from sqlalchemy.orm import selectinload

from .models import (
    User,
    AdDraft,
    AdPhoto,
    AdPublish,
    Settings,
    UserLimit,
    Payment,
    AdStatusEnum,
)


# --------- helpers: timezone-aware now/compare ---------
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_aware_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    # если наивный — помечаем как UTC
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    # если с зоной — приводим к UTC
    return dt.astimezone(timezone.utc)


class Repository:
    """Единая точка доступа к БД."""

    def __init__(self, sessionmaker):
        # AsyncSession factory (async_sessionmaker[AsyncSession])
        self.sessionmaker = sessionmaker

    # ===================== SETTINGS =====================

    async def init_default_settings(self) -> Settings:
        """Гарантирует наличие строки настроек."""
        async with self.sessionmaker() as session:
            st = await session.scalar(sa.select(Settings).limit(1))
            if st:
                return st
            st = Settings(rules_markdown="", channels_json={})
            session.add(st)
            await session.commit()
            await session.refresh(st)
            return st

    async def get_settings(self) -> Optional[Settings]:
        async with self.sessionmaker() as session:
            return await session.scalar(sa.select(Settings).limit(1))

    # совместимость с хендлерами: set_rules/update_rules
    async def set_rules(self, text: str) -> None:
        await self.update_rules(text)

    async def update_rules(self, text: str) -> None:
        async with self.sessionmaker() as session:
            st = await session.scalar(sa.select(Settings).limit(1))
            if not st:
                st = Settings(rules_markdown=text or "", channels_json={})
                session.add(st)
            else:
                st.rules_markdown = text or ""
            await session.commit()

    async def set_channels(self, data: dict) -> None:
        async with self.sessionmaker() as session:
            st = await session.scalar(sa.select(Settings).limit(1))
            if not st:
                st = Settings(rules_markdown="", channels_json=data or {})
                session.add(st)
            else:
                st.channels_json = data or {}
            await session.commit()

    # ======================= USERS ======================

    async def clear_user_drafts(self, user_id: int) -> None:
        """
        Полностью удаляет все черновики пользователя (и фото) со статусом DRAFT.
        Нужен, чтобы новые объявления начинались «с нуля» и фото не тянулись.
        """
        async with self.sessionmaker() as session:
            subq = sa.select(AdDraft.id).where(
                AdDraft.user_id == user_id, AdDraft.status == AdStatusEnum.DRAFT
            )
            await session.execute(sa.delete(AdPhoto).where(AdPhoto.draft_id.in_(subq)))
            await session.execute(sa.delete(AdDraft).where(
                AdDraft.user_id == user_id, AdDraft.status == AdStatusEnum.DRAFT
            ))
            await session.commit()

    async def create_or_get_user(
        self,
        telegram_id: int,
        username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
    ) -> User:
        async with self.sessionmaker() as session:
            user = await session.scalar(sa.select(User).where(User.telegram_id == telegram_id))
            if user:
                # обновим актуальные поля
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                await session.commit()
                await session.refresh(user)
                return user

            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """
        Возвращает пользователя по username.
        Поддерживает ввод с @ и без, сравнение регистронезависимое.
        """
        if not username:
            return None
        uname = username.strip()
        if uname.startswith("@"):
            uname = uname[1:]
        if not uname:
            return None

        async with self.sessionmaker() as session:
            return await session.scalar(
                sa.select(User).where(sa.func.lower(User.username) == uname.lower())
            )

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        async with self.sessionmaker() as session:
            return await session.scalar(sa.select(User).where(User.telegram_id == telegram_id))

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        async with self.sessionmaker() as session:
            return await session.get(User, user_id)

    async def set_user_lang(self, user_id: int, lang: str) -> None:
        async with self.sessionmaker() as session:
            user = await session.get(User, user_id)
            if not user:
                return
            user.lang = (lang or "ru")[:2]
            await session.commit()

    # ======================= DRAFTS =====================

    async def get_active_draft(self, user_id: int) -> Optional[AdDraft]:
        async with self.sessionmaker() as session:
            return await session.scalar(
                sa.select(AdDraft)
                .where(AdDraft.user_id == user_id, AdDraft.status == AdStatusEnum.DRAFT)
                .order_by(AdDraft.updated_at.desc())
                .limit(1)
            )

    async def create_draft(self, user_id: int, ad_type: str) -> AdDraft:
        async with self.sessionmaker() as session:
            draft = AdDraft(
                user_id=user_id,
                type=ad_type,
                category="",
                subcategory=None,
                name=None,
                short_desc=None,
                condition=None,
                detail_desc=None,
                price=None,
                delivery=None,
                city=None,
                status=AdStatusEnum.DRAFT,
            )
            session.add(draft)
            await session.commit()
            await session.refresh(draft)
            return draft

    async def update_draft(self, draft_id: int, **fields) -> None:
        if not fields:
            return
        async with self.sessionmaker() as session:
            draft = await session.get(AdDraft, draft_id)
            if not draft:
                return
            for k, v in fields.items():
                setattr(draft, k, v)
            await session.commit()

    async def get_draft(self, draft_id: int) -> Optional[AdDraft]:
        async with self.sessionmaker() as session:
            return await session.scalar(
                sa.select(AdDraft)
                .where(AdDraft.id == draft_id)
                .options(selectinload(AdDraft.photos))
            )

    async def delete_draft(self, draft_id: int, only_if_status_draft: bool = True) -> bool:
        """
        Полностью удаляет черновик и все его фото.
        Если only_if_status_draft=True — удаляет только если статус=DRAFT.
        """
        async with self.sessionmaker() as session:
            draft = await session.get(AdDraft, draft_id)
            if not draft:
                return False
            if only_if_status_draft and draft.status != AdStatusEnum.DRAFT:
                return False
            # удалим фото
            await session.execute(sa.delete(AdPhoto).where(AdPhoto.draft_id == draft_id))
            await session.delete(draft)
            await session.commit()
            return True

    # ======================= PHOTOS =====================

    async def count_draft_photos(self, draft_id: int) -> int:
        async with self.sessionmaker() as session:
            result = await session.execute(
                sa.select(sa.func.count(AdPhoto.id)).where(AdPhoto.draft_id == draft_id)
            )
            return int(result.scalar_one() or 0)

    async def add_photo_to_draft(self, draft_id: int, file_id: str, order: int) -> AdPhoto:
        async with self.sessionmaker() as session:
            p = AdPhoto(draft_id=draft_id, file_id=file_id, sort_order=order)
            session.add(p)
            await session.commit()
            await session.refresh(p)
            return p

    # ===================== PUBLISHING ===================

    async def publish_draft(self, draft_id: int, user_id: int) -> AdPublish:
        async with self.sessionmaker() as session:
            draft = await session.get(AdDraft, draft_id)
            if not draft:
                raise RuntimeError("Draft not found")
            draft.status = AdStatusEnum.PUBLISHED
            pub = AdPublish(user_id=user_id, draft_id=draft_id, is_sold=False)
            session.add(pub)
            await session.commit()
            await session.refresh(pub)
        # сожжём слот публикации уже после коммита
        await self.consume_publish_slot(user_id)
        return pub

    async def attach_publication_messages(self, publish_id: int, channel_id: int, message_ids: List[int]) -> None:
        async with self.sessionmaker() as session:
            pub = await session.get(AdPublish, publish_id)
            if not pub:
                return
            pub.channel_id = int(channel_id)
            pub.message_ids_json = [int(x) for x in (message_ids or [])]
            await session.commit()

    async def list_user_publications(self, user_id: int) -> List[Tuple[AdPublish, AdDraft]]:
        async with self.sessionmaker() as session:
            res = await session.execute(
                sa.select(AdPublish, AdDraft)
                .join(AdDraft, AdDraft.id == AdPublish.draft_id)
                .options(selectinload(AdDraft.photos))  # жадно подгружаем фото
                .where(AdPublish.user_id == user_id)
                .order_by(AdPublish.id.desc())
            )
            return list(res.all())

    async def get_publication_pair(self, publish_id: int) -> Optional[Tuple[AdPublish, AdDraft]]:
        """Возвращает (AdPublish, AdDraft с фото) либо None."""
        async with self.sessionmaker() as session:
            res = await session.execute(
                sa.select(AdPublish, AdDraft)
                .join(AdDraft, AdDraft.id == AdPublish.draft_id)
                .options(selectinload(AdDraft.photos))
                .where(AdPublish.id == publish_id)
                .limit(1)
            )
            row = res.first()
            return (row[0], row[1]) if row else None

    async def get_publication(self, publish_id: int) -> Optional[AdPublish]:
        async with self.sessionmaker() as session:
            return await session.get(AdPublish, publish_id)

    async def set_publish_sold(self, publish_id: int, is_sold: bool) -> None:
        async with self.sessionmaker() as session:
            pub = await session.get(AdPublish, publish_id)
            if not pub:
                return
            pub.is_sold = bool(is_sold)
            await session.commit()

    async def delete_publication(self, publish_id: int) -> None:
        async with self.sessionmaker() as session:
            pub = await session.get(AdPublish, publish_id)
            if not pub:
                return
            await session.delete(pub)
            await session.commit()

    async def count_user_published_total(self, user_id: int) -> int:
        async with self.sessionmaker() as session:
            result = await session.execute(
                sa.select(sa.func.count(AdPublish.id)).where(AdPublish.user_id == user_id)
            )
            return int(result.scalar_one() or 0)

    # ======================== LIMITS ====================

    async def get_user_limit(self, user_id: int) -> Optional[UserLimit]:
        return await self.get_or_create_default_limit(user_id)

    async def get_or_create_default_limit(self, user_id: int) -> UserLimit:
        """
        Стандарт: квота 1 публикация / 7 дней. Если срок истёк — сбрасываем.
        Все времени — aware UTC.
        """
        now = _utcnow()
        async with self.sessionmaker() as session:
            ul = await session.scalar(sa.select(UserLimit).where(UserLimit.user_id == user_id))
            if ul is None:
                ul = UserLimit(
                    user_id=user_id,
                    mode="quota",
                    quota_total=1,
                    quota_used=0,
                    started_at=now,
                    expires_at=now + timedelta(days=7),
                )
                session.add(ul)
                await session.commit()
                await session.refresh(ul)
                return ul

            exp = _to_aware_utc(ul.expires_at)
            if exp and exp <= now:
                ul.mode = "quota"
                ul.quota_total = 1
                ul.quota_used = 0
                ul.started_at = now
                ul.expires_at = now + timedelta(days=7)
                await session.commit()
                await session.refresh(ul)
            return ul

    async def reset_to_weekly(self, user_id: int, start_from: Optional[datetime] = None) -> UserLimit:
        """Жёсткий сброс к стандарту 1/неделю."""
        now = _to_aware_utc(start_from) or _utcnow()
        async with self.sessionmaker() as session:
            ul = await session.scalar(sa.select(UserLimit).where(UserLimit.user_id == user_id))
            if ul is None:
                ul = UserLimit(
                    user_id=user_id,
                    mode="quota",
                    quota_total=1,
                    quota_used=0,
                    started_at=now,
                    expires_at=now + timedelta(days=7),
                )
                session.add(ul)
            else:
                ul.mode = "quota"
                ul.quota_total = 1
                ul.quota_used = 0
                ul.started_at = now
                ul.expires_at = now + timedelta(days=7)
            await session.commit()
            await session.refresh(ul)
            return ul

    # совместимость с хендлерами
    async def reset_limit_to_default(self, user_id: int) -> UserLimit:
        return await self.reset_to_weekly(user_id)

    async def set_unlimited_month(self, user_id: int) -> UserLimit:
        """Чистый безлимит на 30 дней (mode='unlimited')."""
        async with self.sessionmaker() as session:
            now = _utcnow()
            ul = await session.scalar(sa.select(UserLimit).where(UserLimit.user_id == user_id))
            if ul is None:
                ul = UserLimit(user_id=user_id)
                session.add(ul)
            ul.mode = "unlimited"
            ul.quota_total = None
            ul.quota_used = 0
            ul.started_at = now
            ul.expires_at = now + timedelta(days=30)
            await session.commit()
            await session.refresh(ul)
            return ul

    async def set_quota_month(self, user_id: int, total: int) -> UserLimit:
        """Квота N объявлений на 30 дней (mode='quota')."""
        async with self.sessionmaker() as session:
            now = _utcnow()
            total = max(1, int(total))
            ul = await session.scalar(sa.select(UserLimit).where(UserLimit.user_id == user_id))
            if ul is None:
                ul = UserLimit(user_id=user_id)
                session.add(ul)
            ul.mode = "quota"
            ul.quota_total = total
            ul.quota_used = 0
            ul.started_at = now
            ul.expires_at = now + timedelta(days=30)
            await session.commit()
            await session.refresh(ul)
            return ul

    async def add_extra_one(self, user_id: int) -> UserLimit:
        """
        Покупка «ещё 1 объявление».
        Логика:
          - если период отсутствует/истёк/не quota/квота <= 1 — нормализуем на 30 дней quota;
          - увеличиваем quota_total на 1;
          - если до конца периода < 1 дня — продлеваем до 30 дней от сейчас.
        """
        now = _utcnow()
        async with self.sessionmaker() as session:
            ul = await session.scalar(sa.select(UserLimit).where(UserLimit.user_id == user_id))
            if ul is None:
                ul = UserLimit(user_id=user_id)
                session.add(ul)

            exp = _to_aware_utc(ul.expires_at)

            if exp is None or exp <= now or ul.mode != "quota" or (ul.quota_total or 0) <= 1:
                ul.mode = "quota"
                ul.quota_total = max(ul.quota_total or 1, 1)
                ul.quota_used = 0 if ul.quota_used is None else ul.quota_used
                ul.started_at = now
                ul.expires_at = now + timedelta(days=30)

            if ul.quota_total is None:
                ul.quota_total = 0
            ul.quota_total += 1

            exp = _to_aware_utc(ul.expires_at)
            if exp is None or (exp - now) < timedelta(days=1):
                ul.expires_at = now + timedelta(days=30)

            await session.commit()
            await session.refresh(ul)
            return ul

    async def consume_publish_slot(self, user_id: int) -> None:
        """Отмечает использование слота публикации (кроме безлимита)."""
        async with self.sessionmaker() as session:
            ul = await session.scalar(sa.select(UserLimit).where(UserLimit.user_id == user_id))
            if not ul or ul.mode == "unlimited" or ul.quota_total is None:
                return
            if ul.quota_used is None:
                ul.quota_used = 0
            ul.quota_used += 1
            await session.commit()

    async def reset_limit_to_default(self, user_id: int):
        """Алиас, чтобы совпадало с вызовами из admin.py."""
        return await self.reset_to_weekly(user_id)

    async def get_publish_availability(self, user_id: int) -> tuple[bool, int]:
        """
        Возвращает (can_publish, seconds_left).
        seconds_left > 0 только если слот исчерпан и ждём истечения периода.
        """
        ul = await self.get_or_create_default_limit(user_id)
        # Безлимит
        if ul.mode == "unlimited" or ul.quota_total is None:
            return True, 0

        total = ul.quota_total or 0
        used = ul.quota_used or 0
        if used < total:
            return True, 0

        now = _utcnow()
        exp = _to_aware_utc(ul.expires_at)
        left = 0
        if exp:
            left = int(max(0, (exp - now).total_seconds()))
        return False, left


    # ======================= PAYMENTS ===================

    async def create_payment(self, user_id: int, kind: str, amount: int) -> Payment:
        async with self.sessionmaker() as session:
            p = Payment(user_id=user_id, kind=kind, amount=int(amount), status="pending")
            session.add(p)
            await session.commit()
            await session.refresh(p)
            return p

    async def set_payment_file(self, payment_id: int, file_type: str, file_id: str) -> None:
        async with self.sessionmaker() as session:
            p = await session.get(Payment, payment_id)
            if not p:
                return
            p.file_type = file_type
            p.file_id = file_id
            await session.commit()

    # совместимость: attach_payment_receipt -> set_payment_file
    async def attach_payment_receipt(self, payment_id: int, file_type: str, file_id: str) -> None:
        await self.set_payment_file(payment_id, file_type=file_type, file_id=file_id)

    async def list_pending_payments(self) -> List[Payment]:
        async with self.sessionmaker() as session:
            res = await session.execute(
                sa.select(Payment).where(Payment.status == "pending").order_by(Payment.id.asc())
            )
            return list(res.scalars().all())

    async def get_payment(self, payment_id: int) -> Optional[Payment]:
        async with self.sessionmaker() as session:
            return await session.get(Payment, payment_id)

    async def mark_payment_status(self, payment_id: int, status: str, admin_id: Optional[int] = None) -> None:
        async with self.sessionmaker() as session:
            p = await session.get(Payment, payment_id)
            if not p:
                return
            p.status = status
            p.admin_id = admin_id
            p.processed_at = _utcnow()
            await session.commit()

    async def apply_payment_effect(self, payment: Payment):
        """
        Применяет эффект покупки:
          - extra      -> add_extra_one
          - unlimited  -> set_unlimited_month
          - pin        -> (пока без логики, только approve)
        """
        if payment.kind == "extra":
            return await self.add_extra_one(payment.user_id)
        if payment.kind == "unlimited":
            return await self.set_unlimited_month(payment.user_id)
        # kind == "pin" — нет действий в БД
        return None
