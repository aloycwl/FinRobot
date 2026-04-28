from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class BacktestConfig:
    base_lot: float = 0.01
    multiplier: float = 2.0
    max_steps: int = 4
    fee_bps: float = 2.0


def build_trend_signals_from_m1(m1: pd.DataFrame) -> pd.DataFrame:
    """Build 1m trade signals using 5m EMA(5/20) trend filter.

    m1 must contain columns: time, open, high, low, close, tick_volume
    """
    df = m1.copy().sort_values("time").reset_index(drop=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)

    m5 = (
        df.set_index("time")
        .resample("5min")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "tick_volume": "sum"})
        .dropna()
    )
    m5["ema5"] = m5["close"].ewm(span=5).mean()
    m5["ema20"] = m5["close"].ewm(span=20).mean()

    merged = df.merge(m5[["ema5", "ema20"]], left_on=df["time"].dt.floor("5min"), right_index=True, how="left")
    merged = merged.rename(columns={"key_0": "time_5m"})

    merged["signal"] = 0
    merged.loc[(merged["close"] > merged["ema5"]) & (merged["close"] > merged["ema20"]), "signal"] = 1
    merged.loc[(merged["close"] < merged["ema5"]) & (merged["close"] < merged["ema20"]), "signal"] = -1
    return merged


def backtest_trend_martingale(m1: pd.DataFrame, cfg: BacktestConfig) -> dict:
    df = build_trend_signals_from_m1(m1)
    df["ret"] = df["close"].pct_change().fillna(0.0)

    position = 0
    martingale_step = 0
    strategy_returns = []
    trade_returns = []

    for i in range(1, len(df)):
        signal = int(df.loc[i - 1, "signal"])
        step_lot = cfg.base_lot * (cfg.multiplier ** martingale_step)

        if signal != 0:
            r = signal * float(df.loc[i, "ret"]) * step_lot
            fee = (cfg.fee_bps / 10000.0) * step_lot
            r -= fee
            strategy_returns.append(r)

            if position != signal:
                trade_returns.append(r)
                if r < 0:
                    martingale_step = min(martingale_step + 1, cfg.max_steps)
                else:
                    martingale_step = 0
                position = signal
            else:
                trade_returns.append(r)
        else:
            strategy_returns.append(0.0)
            position = 0
            martingale_step = 0

    if not strategy_returns:
        return {"error": "No strategy returns generated."}

    equity = pd.Series(strategy_returns).add(1).cumprod()
    total_return = float(equity.iloc[-1] - 1)
    max_drawdown = float((equity / equity.cummax() - 1).min())
    win_rate = float((pd.Series(trade_returns) > 0).mean()) if trade_returns else 0.0

    return {
        "bars": int(len(df)),
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "num_trades": int(len(trade_returns)),
    }
