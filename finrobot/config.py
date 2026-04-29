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
    mt5_login: int | None = int(os.getenv("MT5_LOGIN") or "0") or None
    mt5_password: str | None = os.getenv("MT5_PASSWORD")
    mt5_server: str | None = os.getenv("MT5_SERVER")
    mt5_symbol: str = os.getenv("MT5_SYMBOL", "XAUUSD")
    mt5_pip_value: float = float(os.getenv("MT5_PIP_VALUE", "0.01"))
    
    # cTrader Configuration
    ctrader_client_id: str | None = os.getenv("CTRADER_CLIENT_ID")
    ctrader_client_secret: str | None = os.getenv("CTRADER_CLIENT_SECRET")
    ctrader_access_token: str | None = os.getenv("CTRADER_ACCESS_TOKEN")
    ctrader_account_id: int | None = int(os.getenv("CTRADER_ACCOUNT_ID") or "0") or None
    ctrader_symbol: str = os.getenv("CTRADER_SYMBOL", "XAUUSD")


settings = Settings()
