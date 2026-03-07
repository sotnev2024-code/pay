from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response

from bot.bot_instance import bot
from bot.services.subscription import activate_subscription
from database import crud
from database.engine import async_session
from database.models import PaymentStatus
from payments.manager import payment_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhook")


async def _process_payment_webhook(provider_name: str, data: dict, headers: dict) -> bool:
    provider = payment_manager.get(provider_name)
    result = await provider.verify_webhook(data, headers)

    if not result.success or result.internal_payment_id is None:
        logger.warning("Webhook verification failed for %s: %s", provider_name, result)
        return False

    async with async_session() as session:
        payment = await session.get(crud.Payment, result.internal_payment_id)
        if payment is None:
            logger.error("Payment %s not found", result.internal_payment_id)
            return False

        if payment.status == PaymentStatus.SUCCESS:
            return True

        await crud.update_payment_status(
            session,
            payment.id,
            PaymentStatus.SUCCESS,
            provider_payment_id=result.provider_payment_id,
        )

        await activate_subscription(
            session, bot, payment.user_id, payment.tariff_id, payment.id
        )

    return True


@router.post("/yookassa")
async def webhook_yookassa(request: Request):
    data = await request.json()
    headers = dict(request.headers)
    success = await _process_payment_webhook("yookassa", data, headers)
    return {"ok": success}


@router.post("/robokassa")
async def webhook_robokassa(request: Request):
    data = dict(await request.form())
    headers = dict(request.headers)
    success = await _process_payment_webhook("robokassa", data, headers)
    if success:
        inv_id = data.get("InvId", "")
        return Response(content=f"OK{inv_id}", media_type="text/plain")
    return Response(content="FAIL", status_code=400)


@router.post("/prodamus")
async def webhook_prodamus(request: Request):
    data = dict(await request.form())
    headers = dict(request.headers)
    success = await _process_payment_webhook("prodamus", data, headers)
    return {"ok": success}


@router.post("/cryptopay")
async def webhook_cryptopay(request: Request):
    body_bytes = await request.body()
    import json
    try:
        data = json.loads(body_bytes)
    except Exception:
        data = {}
    data["_raw_body"] = body_bytes.decode()
    headers = dict(request.headers)
    success = await _process_payment_webhook("cryptopay", data, headers)
    return {"ok": success}
