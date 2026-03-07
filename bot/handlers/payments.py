from __future__ import annotations

import json
import logging

from aiogram import Router
from aiogram.types import Message, PreCheckoutQuery

from bot.bot_instance import bot
from bot.services.subscription import activate_subscription
from database.crud import get_user_by_telegram_id, update_payment_status
from database.engine import async_session
from database.models import PaymentStatus

logger = logging.getLogger(__name__)

router = Router()


@router.pre_checkout_query()
async def handle_pre_checkout(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(lambda msg: msg.successful_payment is not None)
async def handle_successful_payment(message: Message) -> None:
    payment = message.successful_payment
    try:
        payload = json.loads(payment.invoice_payload)
    except (json.JSONDecodeError, TypeError):
        payload = {}

    internal_payment_id = payload.get("payment_id")
    tariff_id = payload.get("tariff_id")

    if not internal_payment_id or not tariff_id:
        logger.error("Stars payment with invalid payload: %s", payload)
        return

    async with async_session() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if user is None:
            return

        provider_payment_id = payment.telegram_payment_charge_id

        db_payment = await update_payment_status(
            session,
            internal_payment_id,
            PaymentStatus.SUCCESS,
            provider_payment_id=provider_payment_id,
        )

        if db_payment:
            await activate_subscription(
                session, bot, user.id, tariff_id, internal_payment_id
            )
