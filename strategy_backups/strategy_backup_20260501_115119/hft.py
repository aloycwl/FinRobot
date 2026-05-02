from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class HFTConfig:
    tick_threshold: float = 0.05
    volume_filter: int = 25
    latency_ms: int = 100
    spread_limit: float = 0.02
    fast_window: int = 5
    slow_window: int = 20
    fee_bps: float = 3.0
    risk_per_trade: float = 0.005


def backtest_hft(df: pd.DataFrame, cfg: HFTConfig) -> dict:
    """Simple tick-based HFT backtest implementation"""
    df = df.copy().sort_values("time").reset_index(drop=True)

    df["price_change"] = df["close"].pct_change().fillna(0.0)
    df["volume_change"] = df["tick_volume"].pct_change().fillna(0.0)

    position = 0
    pnl = []
    trades = []
    entry_price = 0.0

    for i in range(1, len(df)):
        price_move = abs(df.loc[i, "price_change"])
        volume_spike = df.loc[i, "volume_change"] > 2.0

        if price_move > cfg.tick_threshold and volume_spike:
            if position == 0:
                if df.loc[i, "price_change"] > 0:
                    position = 1
                    entry_price = df.loc[i, "close"]
                else:
                    position = -1
                    entry_price = df.loc[i, "close"]
            elif position == 1 and df.loc[i, "price_change"] < 0:
                trade_pnl = (df.loc[i, "close"] - entry_price) / entry_price
                pnl.append(trade_pnl)
                trades.append(trade_pnl)
                position = 0
            elif position == -1 and df.loc[i, "price_change"] > 0:
                trade_pnl = (entry_price - df.loc[i, "close"]) / entry_price
                pnl.append(trade_pnl)
                trades.append(trade_pnl)
                position = 0
        else:
            if position != 0:
                trade_pnl = position * (df.loc[i, "close"] - entry_price) / entry_price
                pnl.append(trade_pnl)

    if not pnl:
        return {
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "num_trades": 0
        }

    equity = pd.Series(pnl).add(1).cumprod()
    total_return = float(equity.iloc[-1] - 1)
    max_drawdown = float((equity / equity.cummax() - 1).min())
    win_rate = float((pd.Series(trades) > 0).mean()) if trades else 0.0

    return {
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "num_trades": len(trades)
    }


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
