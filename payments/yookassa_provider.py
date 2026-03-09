from __future__ import annotations

import uuid
from typing import Optional

from yookassa import Configuration, Payment as YKPayment

from config import settings
from payments.base import PaymentProvider, PaymentResult, PaymentStatusEnum, WebhookResult


class YooKassaProvider(PaymentProvider):
    name = "yookassa"

    def __init__(self) -> None:
        Configuration.account_id = settings.yookassa_shop_id
        Configuration.secret_key = settings.yookassa_secret_key

    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        internal_payment_id: int,
        user_id: int,
        tariff_id: int,
    ) -> PaymentResult:
        payment = YKPayment.create(
            {
                "amount": {"value": f"{amount:.2f}", "currency": "RUB"},
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"{settings.webapp_url}?status=success&pid={internal_payment_id}",
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "payment_id": internal_payment_id,
                    "user_id": user_id,
                    "tariff_id": tariff_id,
                },
            },
            idempotency_key=str(uuid.uuid4()),
        )
        return PaymentResult(
            payment_id=internal_payment_id,
            provider=self.name,
            pay_url=payment.confirmation.confirmation_url,
            raw={"provider_id": payment.id},
        )

    async def verify_webhook(self, data: dict, headers: Optional[dict] = None) -> WebhookResult:
        obj = data.get("object", {})
        metadata = obj.get("metadata") or {}
        yk_status = obj.get("status", "")
        status_map = {
            "succeeded": PaymentStatusEnum.SUCCESS,
            "canceled": PaymentStatusEnum.FAILED,
            "waiting_for_capture": PaymentStatusEnum.PENDING,
        }

        raw_pid = metadata.get("payment_id")
        try:
            internal_payment_id = int(raw_pid) if raw_pid is not None else None
        except (TypeError, ValueError):
            internal_payment_id = None

        return WebhookResult(
            success=yk_status == "succeeded",
            provider_payment_id=obj.get("id"),
            internal_payment_id=internal_payment_id,
            status=status_map.get(yk_status, PaymentStatusEnum.PENDING),
            raw=data,
        )

    async def check_payment_status(self, provider_payment_id: str) -> PaymentStatusEnum:
        payment = YKPayment.find_one(provider_payment_id)
        if payment.status == "succeeded":
            return PaymentStatusEnum.SUCCESS
        if payment.status == "canceled":
            return PaymentStatusEnum.FAILED
        return PaymentStatusEnum.PENDING

    async def refund(self, provider_payment_id: str) -> bool:
        from yookassa import Refund
        try:
            payment = YKPayment.find_one(provider_payment_id)
            Refund.create(
                {
                    "payment_id": provider_payment_id,
                    "amount": payment.amount,
                },
                idempotency_key=str(uuid.uuid4()),
            )
            return True
        except Exception:
            return False
