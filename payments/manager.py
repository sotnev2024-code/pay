from __future__ import annotations

from typing import Any, Dict, List

from config import settings
from payments.base import PaymentProvider


class PaymentManager:
    def __init__(self) -> None:
        self._providers: Dict[str, PaymentProvider] = {}

    def register(self, provider: PaymentProvider) -> None:
        self._providers[provider.name] = provider

    def get(self, name: str) -> PaymentProvider:
        provider = self._providers.get(name)
        if provider is None:
            raise ValueError("Payment provider '%s' is not registered" % name)
        return provider

    @property
    def available(self) -> List[str]:
        return list(self._providers.keys())

    def provider_display_info(self) -> List[Dict[str, Any]]:
        mapping = {
            "stars": {"label": "Telegram Stars", "icon": "⭐", "currency": "XTR"},
            "yookassa": {"label": "ЮKassa (карта)", "icon": "💳", "currency": "RUB"},
            "robokassa": {"label": "Robokassa", "icon": "🏦", "currency": "RUB"},
            "prodamus": {"label": "Prodamus", "icon": "💰", "currency": "RUB"},
            "cryptopay": {"label": "Crypto Bot", "icon": "🪙", "currency": "USDT"},
        }
        result = []
        for name in self._providers:
            info = mapping.get(name, {"label": name, "icon": "💵", "currency": "USD"})
            info["name"] = name
            result.append(info)
        return result


payment_manager = PaymentManager()


def init_providers() -> None:
    """Register all providers whose credentials are present in .env."""
    if settings.yookassa_enabled:
        from payments.yookassa_provider import YooKassaProvider
        payment_manager.register(YooKassaProvider())

    if settings.robokassa_enabled:
        from payments.robokassa_provider import RobokassaProvider
        payment_manager.register(RobokassaProvider())

    if settings.prodamus_enabled:
        from payments.prodamus_provider import ProdamusProvider
        payment_manager.register(ProdamusProvider())

    if settings.cryptopay_enabled:
        from payments.cryptopay_provider import CryptoPayProvider
        payment_manager.register(CryptoPayProvider())
