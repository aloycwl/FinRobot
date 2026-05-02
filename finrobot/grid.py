from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class GridConfig:
    # Trend filter settings (5min chart)
    trend_ema_fast: int = 5
    trend_ema_slow: int = 15
    trend_timeframe: str = "5min"
    ema_fast: int = 5
    ema_slow: int = 15
    
    # Grid execution settings (1min chart)
    grid_step_pips: float = 5.0
    grid_step: float = 5.0
    take_profit_pips: float = 1.0
    max_grid_levels: int = 6
    base_lot: float = 0.01
    fee_bps: float = 2.0
    pip_value: float = 0.01  # XAUUSD = 0.01 per pip


def calculate_trend_direction(df_m1: pd.DataFrame, cfg: GridConfig) -> pd.DataFrame:
    """Calculate overall trend direction using 5min EMA 5/15 crossover"""
    df = df_m1.copy().reset_index()
    
    # Handle various index/column naming conventions
    # Data from CSV has 'time' column, but may be set as index
    if 'index' in df.columns:
        # If index was reset and is datetime, use it as time
        if pd.api.types.is_datetime64_any_dtype(df['index']):
            df = df.rename(columns={'index': 'time'})
    
    # Handle both 'date' and 'time' columns
    if "date" in df.columns and "time" not in df.columns:
        df = df.rename(columns={"date": "time"})
    if "time" in df.columns and "date" not in df.columns:
        df["date"] = df["time"]
        
    # Ensure time column exists and is datetime
    if "time" not in df.columns:
        raise ValueError("DataFrame must have 'time' column or datetime index")
        
    df["time"] = pd.to_datetime(df["time"], utc=True)
    
    # Resample to 5 minute timeframe for trend filter
    df_5m = (
        df.set_index("time")
        .resample(cfg.trend_timeframe)
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna()
    )
    
    df_5m["ema5"] = df_5m["close"].ewm(span=cfg.trend_ema_fast).mean()
    df_5m["ema15"] = df_5m["close"].ewm(span=cfg.trend_ema_slow).mean()
    df_5m["trend"] = 0
    df_5m.loc[df_5m["ema5"] > df_5m["ema15"], "trend"] = 1   # Bullish
    df_5m.loc[df_5m["ema5"] < df_5m["ema15"], "trend"] = -1  # Bearish
    
    # Merge trend back to 1min dataframe
    merged = df.merge(
        df_5m[["trend"]],
        left_on=df["time"].dt.floor(cfg.trend_timeframe),
        right_index=True,
        how="left"
    ).rename(columns={"key_0": "trend_time"})
    
    return merged


def backtest_xauusd_grid(df_m1: pd.DataFrame, cfg: GridConfig) -> dict:
    """
    Grid trading strategy for XAUUSD:
    1. Determine overall trend on 5min chart with EMA 5/15
    2. Place grid orders every 5 pips in trend direction
    3. Close each position at 1 pip profit
    """
    df = calculate_trend_direction(df_m1, cfg)
    
    # Calculate pip steps
    grid_step = cfg.grid_step_pips * cfg.pip_value
    tp_step = cfg.take_profit_pips * cfg.pip_value
    
    position = 0.0
    active_entries = []  # List of entry prices
    strategy_returns = []
    trades_count = 0
    wins = 0
    
    for i in range(1, len(df)):
        current_price = df.loc[i, "close"]
        trend = df.loc[i, "trend"]
        
        if trend == 0:
            # No clear trend, close all positions
            if active_entries:
                for entry in active_entries:
                    ret = (current_price - entry) * position / entry
                    strategy_returns.append(ret)
                    trades_count +=1
                    if ret > 0: wins +=1
                active_entries.clear()
                position = 0.0
            strategy_returns.append(0.0)
            continue
        
        # Check take profit on existing positions
        remaining = []
        for entry in active_entries:
            if trend == 1:  # Long positions
                if current_price >= entry + tp_step:
                    # Close position for 1 pip profit
                    ret = tp_step / entry * cfg.base_lot
                    strategy_returns.append(ret - (cfg.fee_bps / 10000) * cfg.base_lot)
                    trades_count +=1
                    wins +=1
                else:
                    remaining.append(entry)
            else:  # Short positions
                if current_price <= entry - tp_step:
                    ret = tp_step / entry * cfg.base_lot
                    strategy_returns.append(ret - (cfg.fee_bps / 10000) * cfg.base_lot)
                    trades_count +=1
                    wins +=1
                else:
                    remaining.append(entry)
        
        active_entries = remaining
        
        # Open new grid positions if within max levels
        if len(active_entries) < cfg.max_grid_levels:
            last_entry = active_entries[-1] if active_entries else current_price
            
            if trend == 1: # Bullish grid - place below current price
                next_grid_level = last_entry - grid_step
                if current_price <= next_grid_level or not active_entries:
                    active_entries.append(current_price)
                    position += cfg.base_lot
                    strategy_returns.append(-(cfg.fee_bps / 10000) * cfg.base_lot)
            else: # Bearish grid - place above current price
                next_grid_level = last_entry + grid_step
                if current_price >= next_grid_level or not active_entries:
                    active_entries.append(current_price)
                    position -= cfg.base_lot
                    strategy_returns.append(-(cfg.fee_bps / 10000) * cfg.base_lot)
        else:
            strategy_returns.append(0.0)
    
    # Close any remaining open positions at end of backtest
    if active_entries:
        final_price = df.iloc[-1]["close"]
        for entry in active_entries:
            ret = (final_price - entry) * cfg.base_lot / entry
            strategy_returns.append(ret)
            trades_count +=1
            if ret > 0: wins +=1
    
    equity = pd.Series(strategy_returns).add(1).cumprod()
    total_return = float(equity.iloc[-1] - 1) if len(equity) > 0 else 0.0
    max_drawdown = float((equity / equity.cummax() - 1).min())
    win_rate = wins / trades_count if trades_count > 0 else 0.0
    
    return {
        "bars": len(df),
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "total_trades": trades_count,
        "win_trades": wins,
        "grid_levels_used_max": cfg.max_grid_levels
    }
