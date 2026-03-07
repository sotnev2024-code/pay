from __future__ import annotations

import hashlib
from typing import Optional
from urllib.parse import urlencode

from config import settings
from payments.base import PaymentProvider, PaymentResult, PaymentStatusEnum, WebhookResult

_BASE_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"
_TEST_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


class RobokassaProvider(PaymentProvider):
    name = "robokassa"

    def _sign(self, *parts: str) -> str:
        raw = ":".join(parts)
        return hashlib.md5(raw.encode()).hexdigest()

    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        internal_payment_id: int,
        user_id: int,
        tariff_id: int,
    ) -> PaymentResult:
        login = settings.robokassa_login
        password1 = settings.robokassa_password1

        out_sum = f"{amount:.2f}"
        inv_id = str(internal_payment_id)
        signature = self._sign(login, out_sum, inv_id, password1)

        params = {
            "MerchantLogin": login,
            "OutSum": out_sum,
            "InvId": inv_id,
            "Description": description,
            "SignatureValue": signature,
            "Culture": "ru",
        }
        if settings.robokassa_test_mode:
            params["IsTest"] = "1"

        url = f"{_BASE_URL}?{urlencode(params)}"

        return PaymentResult(
            payment_id=internal_payment_id,
            provider=self.name,
            pay_url=url,
        )

    async def verify_webhook(self, data: dict, headers: Optional[dict] = None) -> WebhookResult:
        out_sum = data.get("OutSum", "")
        inv_id = data.get("InvId", "")
        sig = data.get("SignatureValue", "")

        expected = self._sign(out_sum, inv_id, settings.robokassa_password2)

        if sig.lower() != expected.lower():
            return WebhookResult(success=False, status=PaymentStatusEnum.FAILED)

        return WebhookResult(
            success=True,
            provider_payment_id=inv_id,
            internal_payment_id=int(inv_id) if inv_id.isdigit() else None,
            status=PaymentStatusEnum.SUCCESS,
            raw=data,
        )

    async def check_payment_status(self, provider_payment_id: str) -> PaymentStatusEnum:
        return PaymentStatusEnum.PENDING
