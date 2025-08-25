from __future__ import annotations

import enum
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, JSON, func, Enum, Boolean, BigInteger
)
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    lang = Column(String(2), default="ru")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    drafts = relationship("AdDraft", back_populates="user", cascade="all, delete-orphan")
    limit = relationship("UserLimit", back_populates="user", uselist=False, cascade="all, delete-orphan")


class AdStatusEnum(str, enum.Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    PUBLISHED = "PUBLISHED"


class AdDraft(Base):
    __tablename__ = "ad_drafts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)
    subcategory = Column(String(50))
    name = Column(String(255))
    short_desc = Column(Text)
    condition = Column(String(20))
    detail_desc = Column(Text)
    price = Column(Integer)
    delivery = Column(String(20))  # 'no_ship' | 'country' | None
    city = Column(String(50))
    status = Column(Enum(AdStatusEnum), nullable=False, default=AdStatusEnum.DRAFT)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="drafts")
    photos = relationship(
        "AdPhoto",
        back_populates="draft",
        cascade="all, delete-orphan",
        order_by="AdPhoto.sort_order",
    )


class AdPhoto(Base):
    __tablename__ = "ad_photos"

    id = Column(Integer, primary_key=True)
    draft_id = Column(Integer, ForeignKey("ad_drafts.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String(255), nullable=False)
    sort_order = Column(Integer)

    draft = relationship("AdDraft", back_populates="photos")


class AdPublish(Base):
    __tablename__ = "ad_publishes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    draft_id = Column(Integer, ForeignKey("ad_drafts.id", ondelete="CASCADE"), nullable=False)
    published_at = Column(DateTime(timezone=True), server_default=func.now())

    channel_id = Column(BigInteger)
    message_ids_json = Column(JSON)
    is_sold = Column(Boolean, nullable=False, default=False)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    rules_markdown = Column(Text)
    channels_json = Column(JSON)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserLimit(Base):
    __tablename__ = "user_limits"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    mode = Column(String(16), nullable=False)  # 'unlimited' | 'quota'
    quota_total = Column(Integer)
    quota_used = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="limit")


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    kind = Column(String(16), nullable=False)        # extra | pin | unlimited
    amount = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, default="pending")
    file_type = Column(String(16))                   # photo | document
    file_id = Column(String(512))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    admin_id = Column(Integer)
