from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from bot.bot_instance import bot
from config import settings
from database import crud
from database.engine import async_session
from payments.manager import payment_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


# ── Telegram initData validation ─────────────────────────────────────

def _validate_init_data(init_data: str) -> Optional[dict]:
    """Validate Telegram WebApp initData HMAC signature. Returns parsed data or None."""
    try:
        parsed = parse_qs(init_data, keep_blank_values=True)
        received_hash = parsed.get("hash", [""])[0]
        if not received_hash:
            return None

        data_pairs = []
        for key, values in sorted(parsed.items()):
            if key == "hash":
                continue
            data_pairs.append(f"{key}={values[0]}")
        data_check_string = "\n".join(data_pairs)

        secret_key = hmac.new(
            b"WebAppData", settings.bot_token.encode(), hashlib.sha256
        ).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            return None

        user_str = parsed.get("user", [""])[0]
        if user_str:
            return json.loads(user_str)
        return {}
    except Exception:
        return None


def _get_user_from_request(request: Request) -> dict:
    """Extract and validate Telegram user from initData header."""
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        raise HTTPException(status_code=401, detail="Missing initData")
    user_data = _validate_init_data(init_data)
    if user_data is None:
        raise HTTPException(status_code=403, detail="Invalid initData signature")
    return user_data


# ── Schemas ──────────────────────────────────────────────────────────

class PaymentCreateRequest(BaseModel):
    tariff_id: int
    provider: str
    promo_code: Optional[str] = None


class PromoValidateRequest(BaseModel):
    code: str
    tariff_id: Optional[int] = None


# ── Endpoints ────────────────────────────────────────────────────────

def _tariff_to_dict(t) -> dict:
    """Serialize tariff for API; handle enum and features robustly."""
    tt = getattr(t.tariff_type, "value", t.tariff_type) if t.tariff_type else "subscription"
    feats = t.features
    if feats is not None and not isinstance(feats, list):
        feats = list(feats.values()) if isinstance(feats, dict) else []
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description or "",
        "price_stars": t.price_stars,
        "price_rub": t.price_rub,
        "price_usd": t.price_usd,
        "duration_days": t.duration_days,
        "tariff_type": tt,
        "level": t.level,
        "features": feats or [],
    }


@router.get("/tariffs")
async def get_tariffs():
    async with async_session() as session:
        tariffs = await crud.get_active_tariffs(session)
        return [_tariff_to_dict(t) for t in tariffs]


@router.get("/profile")
async def get_profile(request: Request):
    init_data = request.headers.get("X-Telegram-Init-Data", "")
    if not init_data:
        return {"user": None, "subscription": None}
    try:
        tg_user = _get_user_from_request(request)
    except HTTPException:
        return {"user": None, "subscription": None}
    telegram_id = tg_user.get("id")
    if not telegram_id:
        return {"user": None, "subscription": None}

    async with async_session() as session:
        user = await crud.get_user_by_telegram_id(session, telegram_id)
        if user is None:
            return {"user": None, "subscription": None}

        sub = await crud.get_active_subscription(session, user.id)
        sub_data = None
        if sub:
            days_left = None
            if sub.expires_at:
                now = datetime.now(timezone.utc)
                days_left = max(
                    (sub.expires_at.replace(tzinfo=timezone.utc) - now).days, 0
                )
            sub_data = {
                "tariff_name": sub.tariff.name if sub.tariff else "",
                "status": sub.status.value,
                "started_at": sub.started_at.isoformat() if sub.started_at else None,
                "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
                "days_left": days_left,
                "duration_days": sub.tariff.duration_days if sub.tariff else None,
                "invite_link": sub.invite_link,
            }

        return {
            "user": {
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "is_admin": user.is_admin,
                "photo_url": tg_user.get("photo_url"),
            },
            "subscription": sub_data,
        }


@router.get("/providers")
async def get_providers():
    return payment_manager.provider_display_info()


@router.post("/promo/validate")
async def validate_promo(body: PromoValidateRequest, request: Request):
    _get_user_from_request(request)

    async with async_session() as session:
        promo = await crud.validate_promo_code(session, body.code, body.tariff_id)
        if promo is None:
            raise HTTPException(404, "Промокод не найден или недействителен")
        return {
            "code": promo.code,
            "discount_percent": promo.discount_percent,
            "discount_amount": promo.discount_amount,
        }


@router.post("/payment/create")
async def create_payment(body: PaymentCreateRequest, request: Request):
    tg_user = _get_user_from_request(request)
    telegram_id = tg_user.get("id")
    if not telegram_id:
        raise HTTPException(400, "No user id")

    async with async_session() as session:
        user = await crud.get_user_by_telegram_id(session, telegram_id)
        if user is None:
            user = await crud.get_or_create_user(
                session,
                telegram_id=telegram_id,
                username=tg_user.get("username"),
                first_name=tg_user.get("first_name", ""),
            )

        tariff = await crud.get_tariff_by_id(session, body.tariff_id)
        if tariff is None:
            raise HTTPException(404, "Тариф не найден")

        currency_map = {
            "stars": ("XTR", tariff.price_stars),
            "yookassa": ("RUB", tariff.price_rub),
            "robokassa": ("RUB", tariff.price_rub),
            "prodamus": ("RUB", tariff.price_rub),
            "cryptopay": ("USDT", tariff.price_usd),
        }
        currency, amount = currency_map.get(body.provider, ("RUB", tariff.price_rub))

        promo_code_id = None
        if body.promo_code:
            promo = await crud.validate_promo_code(session, body.promo_code, tariff.id)
            if promo:
                promo_code_id = promo.id
                if promo.discount_percent:
                    amount = amount * (100 - promo.discount_percent) / 100
                elif promo.discount_amount:
                    amount = max(amount - promo.discount_amount, 1)
                await crud.use_promo_code(session, promo.id)

        amount = round(amount, 2) if isinstance(amount, float) else amount

        db_payment = await crud.create_payment(
            session,
            user_id=user.id,
            tariff_id=tariff.id,
            provider=body.provider,
            amount=amount,
            currency=currency,
            promo_code_id=promo_code_id,
        )

        try:
            provider = payment_manager.get(body.provider)
        except ValueError:
            raise HTTPException(400, f"Провайдер '{body.provider}' не поддерживается")

        result = await provider.create_payment(
            amount=amount,
            currency=currency,
            description=tariff.name,
            internal_payment_id=db_payment.id,
            user_id=user.id,
            tariff_id=tariff.id,
        )

        if result.raw.get("provider_id"):
            await crud.update_payment_status(
                session,
                db_payment.id,
                crud.PaymentStatus.PENDING,
                provider_payment_id=result.raw["provider_id"],
            )

        return {
            "payment_id": db_payment.id,
            "provider": body.provider,
            "pay_url": result.pay_url,
            "invoice_link": result.invoice_link,
        }
