from __future__ import annotations

import hashlib
import hmac
import json
from urllib.parse import urlencode

from config import settings
from payments.base import PaymentProvider, PaymentResult, PaymentStatusEnum, WebhookResult


def _hmac_sign(data: str, secret: str) -> str:
    return hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()


class ProdamusProvider(PaymentProvider):
    name = "prodamus"

    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        internal_payment_id: int,
        user_id: int,
        tariff_id: int,
    ) -> PaymentResult:
        params = {
            "order_id": str(internal_payment_id),
            "products[0][name]": description,
            "products[0][price]": f"{amount:.2f}",
            "products[0][quantity]": "1",
            "do": "link",
            "customer_extra": json.dumps({"uid": user_id, "tid": tariff_id}),
            "urlReturn": f"{settings.webapp_url}?status=success&pid={internal_payment_id}",
            "urlNotification": f"{settings.webhook_url}/api/webhook/prodamus",
        }

        sign = _hmac_sign(urlencode(params, doseq=True), settings.prodamus_secret)
        params["signature"] = sign

        url = f"{settings.prodamus_link}?{urlencode(params, doseq=True)}"

        return PaymentResult(
            payment_id=internal_payment_id,
            provider=self.name,
            pay_url=url,
        )

    async def verify_webhook(self, data: dict, headers: dict | None = None) -> WebhookResult:
        received_sign = data.pop("signature", "")
        body_str = urlencode(data, doseq=True)
        expected_sign = _hmac_sign(body_str, settings.prodamus_secret)

        if not hmac.compare_digest(received_sign, expected_sign):
            return WebhookResult(success=False, status=PaymentStatusEnum.FAILED)

        order_id = data.get("order_id", "")
        payment_status = data.get("payment_status", "")

        status = PaymentStatusEnum.SUCCESS if payment_status == "success" else PaymentStatusEnum.FAILED

        return WebhookResult(
            success=payment_status == "success",
            provider_payment_id=data.get("payment_id"),
            internal_payment_id=int(order_id) if order_id.isdigit() else None,
            status=status,
            raw=data,
        )

    async def check_payment_status(self, provider_payment_id: str) -> PaymentStatusEnum:
        return PaymentStatusEnum.PENDING
