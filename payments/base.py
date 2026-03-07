from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class PaymentResult:
    """Returned by create_payment — tells the frontend how to proceed."""
    payment_id: int
    provider: str
    pay_url: Optional[str] = None
    invoice_link: Optional[str] = None
    raw: Dict = field(default_factory=dict)


@dataclass
class WebhookResult:
    """Returned by verify_webhook after signature validation."""
    success: bool
    provider_payment_id: Optional[str] = None
    internal_payment_id: Optional[int] = None
    status: PaymentStatusEnum = PaymentStatusEnum.PENDING
    raw: Dict = field(default_factory=dict)


class PaymentProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def create_payment(
        self,
        amount: float,
        currency: str,
        description: str,
        internal_payment_id: int,
        user_id: int,
        tariff_id: int,
    ) -> PaymentResult:
        ...

    @abstractmethod
    async def verify_webhook(self, data: dict, headers: Optional[dict] = None) -> WebhookResult:
        ...

    @abstractmethod
    async def check_payment_status(self, provider_payment_id: str) -> PaymentStatusEnum:
        ...

    async def refund(self, provider_payment_id: str) -> bool:
        return False
