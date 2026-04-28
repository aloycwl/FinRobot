from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    okx_symbol: str = os.getenv("OKX_SYMBOL", "BTC-USDT")
    okx_bar: str = os.getenv("OKX_BAR", "5m")
    cryptopanic_token: str | None = os.getenv("CP")
    nvidia_key: str | None = os.getenv("NV")
    nvidia_model: str = os.getenv("NVIDIA_MODEL", "qwen/qwen3-235b-a22b")
    mt5_login: int | None = int(os.getenv("MT5_LOGIN", "0")) or None
    mt5_password: str | None = os.getenv("MT5_PASSWORD")
    mt5_server: str | None = os.getenv("MT5_SERVER")


settings = Settings()
