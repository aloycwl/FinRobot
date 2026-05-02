from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass
class BacktestConfig:
    base_lot: float = 0.01
    multiplier: float = 2.0
    max_steps: int = 4
    fee_bps: float = 2.0
    ema_fast: int = 5
    ema_slow: int = 20


def build_trend_signals_from_m1(m1: pd.DataFrame, cfg: BacktestConfig) -> pd.DataFrame:
    """Build 1m trade signals using 5m EMA(5/20) trend filter.

    m1 must contain columns: time, open, high, low, close, tick_volume
    """
    df = m1.copy()
    
    # Handle index being datetime
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index(names="time")
    
    # Handle both 'date' and 'time' columns
    if "date" in df.columns and "time" not in df.columns:
        df = df.rename(columns={"date": "time"})
        
    df = df.sort_values("time").reset_index(drop=True)
    df["time"] = pd.to_datetime(df["time"], utc=True)

    # Handle both tick_volume and volume column names
    volume_col = "tick_volume" if "tick_volume" in df.columns else "volume"
    
    m5 = (
        df.set_index("time")
        .resample("5min")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", volume_col: "sum"})
        .dropna()
    )
    m5.rename(columns={volume_col: "tick_volume"}, inplace=True)
    m5["ema_fast"] = m5["close"].ewm(span=cfg.ema_fast).mean()
    m5["ema_slow"] = m5["close"].ewm(span=cfg.ema_slow).mean()

    merged = df.merge(m5[["ema_fast", "ema_slow"]], left_on=df["time"].dt.floor("5min"), right_index=True, how="left")
    merged = merged.rename(columns={"key_0": "time_5m"})

    merged["signal"] = 0
    merged.loc[(merged["close"] > merged["ema_fast"]) & (merged["close"] > merged["ema_slow"]), "signal"] = 1
    merged.loc[(merged["close"] < merged["ema_fast"]) & (merged["close"] < merged["ema_slow"]), "signal"] = -1
    return merged


def backtest_trend_martingale(m1: pd.DataFrame, cfg: BacktestConfig) -> dict:
    df = build_trend_signals_from_m1(m1, cfg)
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
