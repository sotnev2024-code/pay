from __future__ import annotations

import enum
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TariffType(str, enum.Enum):
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one_time"
    MEMBERSHIP = "membership"


class SubStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255), default="")
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    subscriptions: Mapped[List[Subscription]] = relationship(back_populates="user")
    payments: Mapped[List[Payment]] = relationship(back_populates="user")


class Tariff(Base):
    __tablename__ = "tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    price_stars: Mapped[int] = mapped_column(Integer, default=0)
    price_rub: Mapped[float] = mapped_column(Float, default=0.0)
    price_usd: Mapped[float] = mapped_column(Float, default=0.0)
    duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tariff_type: Mapped[TariffType] = mapped_column(
        Enum(TariffType), default=TariffType.SUBSCRIPTION
    )
    level: Mapped[int] = mapped_column(Integer, default=0)
    features: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    subscriptions: Mapped[List[Subscription]] = relationship(back_populates="tariff")
    payments: Mapped[List[Payment]] = relationship(back_populates="tariff")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))
    status: Mapped[SubStatus] = mapped_column(Enum(SubStatus), default=SubStatus.ACTIVE)
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    invite_link: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    notified_3d: Mapped[bool] = mapped_column(Boolean, default=False)
    notified_1d: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped[User] = relationship(back_populates="subscriptions")
    tariff: Mapped[Tariff] = relationship(back_populates="subscriptions")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    tariff_id: Mapped[int] = mapped_column(ForeignKey("tariffs.id"))
    provider: Mapped[str] = mapped_column(String(50))
    provider_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING
    )
    promo_code_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("promo_codes.id"), nullable=True
    )
    payload: Mapped[Optional[Dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped[User] = relationship(back_populates="payments")
    tariff: Mapped[Tariff] = relationship(back_populates="payments")
    promo_code: Mapped[Optional[PromoCode]] = relationship()


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    discount_percent: Mapped[int] = mapped_column(Integer, default=0)
    discount_amount: Mapped[float] = mapped_column(Float, default=0.0)
    max_uses: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tariff_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tariffs.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class MainMenuSettings(Base):
    __tablename__ = "main_menu_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    photo_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description_html: Mapped[str] = mapped_column(Text, default="")
    button_text: Mapped[str] = mapped_column(String(255), default="Оформить подписку")
    button_color: Mapped[str] = mapped_column(String(20), default="green")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class AutoBroadcastTriggerType(str, enum.Enum):
    DAYS_BEFORE_EXPIRY = "days_before_expiry"
    AFTER_START_NO_PAYMENT = "after_start_no_payment"
    AFTER_PAYMENT_DAYS = "after_payment_days"


class AutoBroadcast(Base):
    __tablename__ = "auto_broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trigger_type: Mapped[AutoBroadcastTriggerType] = mapped_column(
        Enum(AutoBroadcastTriggerType)
    )
    trigger_value: Mapped[int] = mapped_column(Integer, default=0)
    delay_type: Mapped[str] = mapped_column(String(10), default="days")
    delay_value: Mapped[int] = mapped_column(Integer, default=0)
    message_photo_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    message_text_html: Mapped[str] = mapped_column(Text, default="")
    button_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    button_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    button_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SentAutoBroadcast(Base):
    __tablename__ = "sent_auto_broadcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    auto_broadcast_id: Mapped[int] = mapped_column(ForeignKey("auto_broadcasts.id"))
    sent_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
