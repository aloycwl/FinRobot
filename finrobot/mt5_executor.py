from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time

import pandas as pd

from .hft import TrendMartingaleConfig, next_martingale_lot, trend_signal_1m_with_5m_filter


@dataclass
class MT5Credentials:
    login: int
    password: str
    server: str


def connect(credentials: MT5Credentials):
    import MetaTrader5 as mt5

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    if not mt5.login(credentials.login, password=credentials.password, server=credentials.server):
        code = mt5.last_error()
        mt5.shutdown()
        raise RuntimeError(f"MT5 login failed: {code}")
    return mt5


def fetch_rates(mt5, symbol: str, timeframe: int, bars: int) -> pd.DataFrame:
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No rates returned for {symbol}")
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    return frame


def place_market_order(mt5, symbol: str, side: str, lot: float, deviation: int = 20):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"Symbol unavailable: {symbol}")
    order_type = mt5.ORDER_TYPE_BUY if side.lower() == "buy" else mt5.ORDER_TYPE_SELL
    price = tick.ask if side.lower() == "buy" else tick.bid
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "deviation": deviation,
        "magic": 20260428,
        "comment": "finrobot-auto",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Order failed: {result}")
    return result


def _latest_closed_profit(mt5, symbol: str) -> float | None:
    now = datetime.now(timezone.utc)
    deals = mt5.history_deals_get(now - timedelta(days=2), now, group=f"*{symbol}*")
    if deals is None:
        return None
    closed = [d for d in deals if getattr(d, "entry", None) == mt5.DEAL_ENTRY_OUT]
    if not closed:
        return None
    return float(closed[-1].profit)


def run_trend_martingale_autotrade(
    mt5,
    symbol: str,
    cfg: TrendMartingaleConfig,
    cycles: int = 20,
    sleep_seconds: int = 60,
) -> None:
    martingale_step = 0

    for _ in range(cycles):
        m1 = fetch_rates(mt5, symbol, mt5.TIMEFRAME_M1, 200)
        m5 = fetch_rates(mt5, symbol, mt5.TIMEFRAME_M5, 200)
        signal = trend_signal_1m_with_5m_filter(m1, m5)

        last_profit = _latest_closed_profit(mt5, symbol)
        if last_profit is not None and last_profit < 0:
            martingale_step = min(martingale_step + 1, cfg.max_steps)
        elif last_profit is not None and last_profit > 0:
            martingale_step = 0

        _, lot = next_martingale_lot(martingale_step, cfg)

        open_positions = mt5.positions_get(symbol=symbol)
        if signal == 1 and not open_positions:
            result = place_market_order(mt5, symbol, side="buy", lot=lot)
            print(f"BUY placed lot={lot}: {result}")
        elif signal == -1 and not open_positions:
            result = place_market_order(mt5, symbol, side="sell", lot=lot)
            print(f"SELL placed lot={lot}: {result}")
        else:
            print(f"No trade. signal={signal}, open_positions={len(open_positions) if open_positions else 0}")

        time.sleep(sleep_seconds)


def download_m1_history(mt5, symbol: str, days: int = 365):
    """Download M1 history from MT5 for a lookback window in days."""
    utc_now = datetime.now(timezone.utc)
    utc_from = utc_now - timedelta(days=days)
    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, utc_from, utc_now)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No M1 history returned for {symbol} over {days} days")
    frame = pd.DataFrame(rates)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    return frame


def shutdown(mt5):
    mt5.shutdown()
