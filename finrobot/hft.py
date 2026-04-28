from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class HFTConfig:
    fast_window: int = 5
    slow_window: int = 20
    fee_bps: float = 3.0
    risk_per_trade: float = 0.005


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
