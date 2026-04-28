from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class HFTConfig:
    fast_window: int = 5
    slow_window: int = 20
    fee_bps: float = 3.0
    risk_per_trade: float = 0.005


@dataclass
class TrendMartingaleConfig:
    base_lot: float = 0.01
    multiplier: float = 2.0
    max_steps: int = 4


def generate_signals(frame: pd.DataFrame, cfg: HFTConfig) -> pd.DataFrame:
    df = frame.copy()
    df["fast"] = df["close"].ewm(span=cfg.fast_window).mean()
    df["slow"] = df["close"].ewm(span=cfg.slow_window).mean()
    df["signal"] = 0
    df.loc[df["fast"] > df["slow"], "signal"] = 1
    df.loc[df["fast"] < df["slow"], "signal"] = -1
    return df


def backtest(frame: pd.DataFrame, cfg: HFTConfig) -> dict:
    df = generate_signals(frame, cfg)
    df["returns"] = df["close"].pct_change().fillna(0)
    df["strategy"] = df["signal"].shift(1).fillna(0) * df["returns"]
    trading_fee = cfg.fee_bps / 10000
    trades = (df["signal"].diff().abs() > 0).astype(int)
    df["strategy"] -= trades * trading_fee
    equity = (1 + df["strategy"]).cumprod()
    total_return = float(equity.iloc[-1] - 1)
    max_drawdown = float((equity / equity.cummax() - 1).min())
    win_rate = float((df["strategy"] > 0).mean())
    return {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "bars": len(df),
    }


def trend_signal_1m_with_5m_filter(m1: pd.DataFrame, m5: pd.DataFrame) -> int:
    """Return 1 for long, -1 for short, 0 for no-trade.

    Rule requested:
    - long if 1m close is above 5m EMA5 and EMA20
    - short if 1m close is below 5m EMA5 and EMA20
    """
    if m1.empty or m5.empty:
        return 0
    m5 = m5.copy()
    m5["ema5"] = m5["close"].ewm(span=5).mean()
    m5["ema20"] = m5["close"].ewm(span=20).mean()

    close_1m = float(m1["close"].iloc[-1])
    ema5 = float(m5["ema5"].iloc[-1])
    ema20 = float(m5["ema20"].iloc[-1])

    if close_1m > ema5 and close_1m > ema20:
        return 1
    if close_1m < ema5 and close_1m < ema20:
        return -1
    return 0


def next_martingale_lot(last_step: int, cfg: TrendMartingaleConfig) -> tuple[int, float]:
    step = min(last_step, cfg.max_steps)
    lot = cfg.base_lot * (cfg.multiplier**step)
    return step, round(lot, 4)
