from __future__ import annotations

import json
import logging

from config import settings
from payments.base import PaymentProvider, PaymentResult, PaymentStatusEnum, WebhookResult

logger = logging.getLogger(__name__)


class CryptoPayProvider(PaymentProvider):
    name = "cryptopay"

    def _get_client(self):
        from aiocryptopay import AioCryptoPay, Networks
        network = Networks.TEST_NET if settings.cryptopay_is_testnet else Networks.MAIN_NET
        return AioCryptoPay(token=settings.cryptopay_api_token, network=network)

    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        internal_payment_id: int,
        user_id: int,
        tariff_id: int,
    ) -> PaymentResult:
        client = self._get_client()
        try:
            invoice = await client.create_invoice(
                asset="USDT",
                amount=amount,
                description=description,
                payload=json.dumps({
                    "payment_id": internal_payment_id,
                    "user_id": user_id,
                    "tariff_id": tariff_id,
                }),
            )
            return PaymentResult(
                payment_id=internal_payment_id,
                provider=self.name,
                pay_url=invoice.bot_invoice_url,
                raw={"invoice_id": invoice.invoice_id},
            )
        finally:
            await client.close()

    async def verify_webhook(self, data: dict, headers: dict | None = None) -> WebhookResult:
        client = self._get_client()
        try:
            body_str = data.get("_raw_body", "")
            crypto_pay_signature = (headers or {}).get("crypto-pay-api-signature", "")

            if not client.check_signature(crypto_pay_signature, body_str):
                return WebhookResult(success=False, status=PaymentStatusEnum.FAILED)

            update = data.get("payload", {})
            payload_str = update.get("payload", "{}")
            try:
                payload = json.loads(payload_str)
            except (json.JSONDecodeError, TypeError):
                payload = {}

            cp_status = update.get("status", "")
            status = PaymentStatusEnum.SUCCESS if cp_status == "paid" else PaymentStatusEnum.PENDING

            return WebhookResult(
                success=cp_status == "paid",
                provider_payment_id=str(update.get("invoice_id", "")),
                internal_payment_id=payload.get("payment_id"),
                status=status,
                raw=data,
            )
        finally:
            await client.close()

    async def check_payment_status(self, provider_payment_id: str) -> PaymentStatusEnum:
        client = self._get_client()
        try:
            invoices = await client.get_invoices(invoice_ids=[int(provider_payment_id)])
            if invoices and invoices[0].status == "paid":
                return PaymentStatusEnum.SUCCESS
            return PaymentStatusEnum.PENDING
        finally:
            await client.close()
