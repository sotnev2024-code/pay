from __future__ import annotations

import json

from payments.base import PaymentProvider, PaymentResult, PaymentStatusEnum, WebhookResult


class StarsProvider(PaymentProvider):
    """Telegram Stars — uses built-in Bot Payments API (currency XTR, provider_token='')."""

    name = "stars"

    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        internal_payment_id: int,
        user_id: int,
        tariff_id: int,
    ) -> PaymentResult:
        from bot.bot_instance import bot

        invoice_link = await bot.create_invoice_link(
            title=description,
            description=description,
            payload=json.dumps({
                "payment_id": internal_payment_id,
                "user_id": user_id,
                "tariff_id": tariff_id,
            }),
            provider_token="",
            currency="XTR",
            prices=[{"label": description, "amount": int(amount)}],
        )
        return PaymentResult(
            payment_id=internal_payment_id,
            provider=self.name,
            invoice_link=invoice_link,
            pay_url=invoice_link,
        )

    async def verify_webhook(self, data: dict, headers: dict | None = None) -> WebhookResult:
        payload_str = data.get("invoice_payload", "{}")
        try:
            payload = json.loads(payload_str)
        except (json.JSONDecodeError, TypeError):
            payload = {}

        return WebhookResult(
            success=True,
            provider_payment_id=data.get("telegram_payment_charge_id"),
            internal_payment_id=payload.get("payment_id"),
            status=PaymentStatusEnum.SUCCESS,
            raw=data,
        )

    async def check_payment_status(self, provider_payment_id: str) -> PaymentStatusEnum:
        return PaymentStatusEnum.SUCCESS
