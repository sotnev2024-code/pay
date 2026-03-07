from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import (
    Payment,
    PaymentStatus,
    PromoCode,
    SubStatus,
    Subscription,
    Tariff,
    User,
)


# ── Users ────────────────────────────────────────────────────────────

async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    first_name: str = "",
    language_code: str | None = None,
    is_admin: bool = False,
) -> User:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language_code=language_code,
            is_admin=is_admin,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        user.username = username
        user.first_name = first_name or user.first_name
        await session.commit()
    return user


async def get_user_by_telegram_id(
    session: AsyncSession, telegram_id: int
) -> User | None:
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def count_users(session: AsyncSession) -> int:
    stmt = select(User)
    result = await session.execute(stmt)
    return len(result.scalars().all())


# ── Tariffs ──────────────────────────────────────────────────────────

async def get_active_tariffs(session: AsyncSession) -> Sequence[Tariff]:
    stmt = (
        select(Tariff)
        .where(Tariff.is_active == True)  # noqa: E712
        .order_by(Tariff.sort_order)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_tariff_by_id(session: AsyncSession, tariff_id: int) -> Tariff | None:
    return await session.get(Tariff, tariff_id)


async def create_tariff(session: AsyncSession, **kwargs) -> Tariff:
    tariff = Tariff(**kwargs)
    session.add(tariff)
    await session.commit()
    await session.refresh(tariff)
    return tariff


async def update_tariff(
    session: AsyncSession, tariff_id: int, **kwargs
) -> Tariff | None:
    tariff = await session.get(Tariff, tariff_id)
    if tariff is None:
        return None
    for k, v in kwargs.items():
        setattr(tariff, k, v)
    await session.commit()
    await session.refresh(tariff)
    return tariff


async def delete_tariff(session: AsyncSession, tariff_id: int) -> bool:
    tariff = await session.get(Tariff, tariff_id)
    if tariff is None:
        return False
    tariff.is_active = False
    await session.commit()
    return True


# ── Subscriptions ────────────────────────────────────────────────────

async def get_active_subscription(
    session: AsyncSession, user_id: int
) -> Subscription | None:
    stmt = (
        select(Subscription)
        .options(selectinload(Subscription.tariff))
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubStatus.ACTIVE,
        )
        .order_by(Subscription.expires_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalar_first()


async def create_subscription(
    session: AsyncSession,
    user_id: int,
    tariff_id: int,
    duration_days: int | None,
    invite_link: str | None = None,
    channel_id: int | None = None,
) -> Subscription:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=duration_days) if duration_days else None
    sub = Subscription(
        user_id=user_id,
        tariff_id=tariff_id,
        status=SubStatus.ACTIVE,
        started_at=now,
        expires_at=expires_at,
        invite_link=invite_link,
        channel_id=channel_id,
    )
    session.add(sub)
    await session.commit()
    await session.refresh(sub)
    return sub


async def get_expiring_subscriptions(
    session: AsyncSession, within_days: int
) -> Sequence[Subscription]:
    now = datetime.now(timezone.utc)
    deadline = now + timedelta(days=within_days)
    stmt = (
        select(Subscription)
        .options(selectinload(Subscription.user), selectinload(Subscription.tariff))
        .where(
            Subscription.status == SubStatus.ACTIVE,
            Subscription.expires_at != None,  # noqa: E711
            Subscription.expires_at <= deadline,
            Subscription.expires_at > now,
        )
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_expired_subscriptions(
    session: AsyncSession,
) -> Sequence[Subscription]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(Subscription)
        .options(selectinload(Subscription.user), selectinload(Subscription.tariff))
        .where(
            Subscription.status == SubStatus.ACTIVE,
            Subscription.expires_at != None,  # noqa: E711
            Subscription.expires_at <= now,
        )
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def expire_subscription(session: AsyncSession, sub_id: int) -> None:
    await session.execute(
        update(Subscription)
        .where(Subscription.id == sub_id)
        .values(status=SubStatus.EXPIRED)
    )
    await session.commit()


async def count_active_subscriptions(session: AsyncSession) -> int:
    stmt = select(Subscription).where(Subscription.status == SubStatus.ACTIVE)
    result = await session.execute(stmt)
    return len(result.scalars().all())


# ── Payments ─────────────────────────────────────────────────────────

async def create_payment(
    session: AsyncSession,
    user_id: int,
    tariff_id: int,
    provider: str,
    amount: float,
    currency: str,
    provider_payment_id: str | None = None,
    promo_code_id: int | None = None,
    payload: dict | None = None,
) -> Payment:
    payment = Payment(
        user_id=user_id,
        tariff_id=tariff_id,
        provider=provider,
        provider_payment_id=provider_payment_id,
        amount=amount,
        currency=currency,
        promo_code_id=promo_code_id,
        payload=payload,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def update_payment_status(
    session: AsyncSession,
    payment_id: int,
    status: PaymentStatus,
    provider_payment_id: str | None = None,
) -> Payment | None:
    payment = await session.get(Payment, payment_id)
    if payment is None:
        return None
    payment.status = status
    if provider_payment_id:
        payment.provider_payment_id = provider_payment_id
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_payment_by_provider_id(
    session: AsyncSession, provider: str, provider_payment_id: str
) -> Payment | None:
    stmt = select(Payment).where(
        Payment.provider == provider,
        Payment.provider_payment_id == provider_payment_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_recent_payments(
    session: AsyncSession, limit: int = 20
) -> Sequence[Payment]:
    stmt = (
        select(Payment)
        .options(selectinload(Payment.user), selectinload(Payment.tariff))
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_revenue(
    session: AsyncSession, since: datetime | None = None
) -> float:
    stmt = select(Payment).where(Payment.status == PaymentStatus.SUCCESS)
    if since:
        stmt = stmt.where(Payment.created_at >= since)
    result = await session.execute(stmt)
    payments = result.scalars().all()
    return sum(p.amount for p in payments)


# ── Promo Codes ──────────────────────────────────────────────────────

async def validate_promo_code(
    session: AsyncSession, code: str, tariff_id: int | None = None
) -> PromoCode | None:
    now = datetime.now(timezone.utc)
    stmt = select(PromoCode).where(
        PromoCode.code == code.upper(),
        PromoCode.is_active == True,  # noqa: E712
    )
    result = await session.execute(stmt)
    promo = result.scalar_one_or_none()
    if promo is None:
        return None
    if promo.max_uses and promo.used_count >= promo.max_uses:
        return None
    if promo.valid_until and promo.valid_until.replace(tzinfo=timezone.utc) < now:
        return None
    if promo.tariff_id and tariff_id and promo.tariff_id != tariff_id:
        return None
    return promo


async def use_promo_code(session: AsyncSession, promo_id: int) -> None:
    promo = await session.get(PromoCode, promo_id)
    if promo:
        promo.used_count += 1
        await session.commit()


async def create_promo_code(session: AsyncSession, **kwargs) -> PromoCode:
    kwargs["code"] = kwargs.get("code", "").upper()
    promo = PromoCode(**kwargs)
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def get_all_promo_codes(session: AsyncSession) -> Sequence[PromoCode]:
    stmt = select(PromoCode).order_by(PromoCode.id.desc())
    result = await session.execute(stmt)
    return result.scalars().all()
