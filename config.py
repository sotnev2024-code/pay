from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


def _parse_int_list(v: Union[str, list, int, None]) -> List[int]:
    if v is None:
        return []
    if isinstance(v, int):
        return [v]
    if isinstance(v, list):
        return [int(x) for x in v]
    return [int(x.strip()) for x in str(v).split(",") if x.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str
    admin_ids: List[int] = []
    webapp_url: str = ""
    webhook_url: str = ""
    webhook_path: str = "/api/webhook/telegram"
    channel_ids: List[int] = []

    @field_validator("admin_ids", "channel_ids", mode="before")
    @classmethod
    def _split_comma_ints(cls, v):
        return _parse_int_list(v)

    # YooKassa
    yookassa_shop_id: Optional[str] = None
    yookassa_secret_key: Optional[str] = None

    # Robokassa
    robokassa_login: Optional[str] = None
    robokassa_password1: Optional[str] = None
    robokassa_password2: Optional[str] = None
    robokassa_test_mode: bool = True

    # Prodamus
    prodamus_secret: Optional[str] = None
    prodamus_link: Optional[str] = None

    # CryptoPay
    cryptopay_api_token: Optional[str] = None
    cryptopay_is_testnet: bool = True

    secret_key: str = "change-me"

    use_polling: bool = True

    port: int = 8000

    db_url: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data.db'}"

    @property
    def yookassa_enabled(self) -> bool:
        return bool(self.yookassa_shop_id and self.yookassa_secret_key)

    @property
    def robokassa_enabled(self) -> bool:
        return bool(self.robokassa_login and self.robokassa_password1)

    @property
    def prodamus_enabled(self) -> bool:
        return bool(self.prodamus_secret and self.prodamus_link)

    @property
    def cryptopay_enabled(self) -> bool:
        return bool(self.cryptopay_api_token)

    def active_providers(self) -> List[str]:
        providers: List[str] = []
        if self.yookassa_enabled:
            providers.append("yookassa")
        if self.robokassa_enabled:
            providers.append("robokassa")
        if self.prodamus_enabled:
            providers.append("prodamus")
        if self.cryptopay_enabled:
            providers.append("cryptopay")
        return providers


settings = Settings()  # type: ignore[call-arg]
