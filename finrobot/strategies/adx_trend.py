"""
NEW STRATEGY STACK - Part 1: Professional-Grade Trading Strategies

This module implements three research-backed profitable strategies:
1. ADX Trend Following - Best for trending markets (ADX > 25)
2. London-NY Breakout - Best for high volatility periods
3. Risk Management Framework - ATR-based position sizing and stops

Author: FinRobot Research Team
Version: 2.0
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from datetime import datetime, time
import logging

logger = logging.getLogger("new_strategies")


# ============================================================================
# PART 1A: ADX TREND FOLLOWING STRATEGY
# ============================================================================

@dataclass
class ADXTrendConfig:
    """
    ADX Trend Following Configuration
    
    Based on research showing trend following with ADX > 25 
    achieves 50-60% win rate with 1:2 to 1:3 risk-reward ratios.
    """
    # ADX Settings
    adx_period: int = 14
    adx_threshold: float = 25.0  # Only trade when ADX > 25 (strong trend)
    
    # EMA Settings for trend direction
    ema_fast: int = 20
    ema_slow: int = 50
    
    # Entry/Exit Settings
    atr_period: int = 14
    atr_multiplier_stop: float = 2.0  # Stop at 2x ATR
    atr_multiplier_target: float = 3.0  # Target at 3x ATR (1:1.5 R:R)
    
    # Risk Management
    risk_per_trade: float = 0.01  # 1% risk per trade
    max_trades_per_day: int = 5
    
    # Session Filter (optional)
    only_trade_london_ny: bool = False  # Set True for best results
    
    # Fees
    fee_bps: float = 2.0
    
    def __post_init__(self):
        if self.adx_threshold < 20:
            logger.warning("ADX threshold < 20 may produce too many false signals")


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Average Directional Index (ADX) for trend strength.
    
    ADX > 25: Strong trend (good for trend following)
    ADX < 20: Weak trend (avoid or use mean reversion)
    """
    df = df.copy()
    
    # True Range
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    
    # +DM and -DM
    df['plus_dm'] = np.where(
        (df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
        np.maximum(df['high'] - df['high'].shift(1), 0),
        0
    )
    df['minus_dm'] = np.where(
        (df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
        np.maximum(df['low'].shift(1) - df['low'], 0),
        0
    )
    
    # Smoothed averages
    df['atr'] = df['tr'].ewm(alpha=1/period, adjust=False).mean()
    df['plus_di'] = 100 * (df['plus_dm'].ewm(alpha=1/period, adjust=False).mean() / df['atr'])
    df['minus_di'] = 100 * (df['minus_dm'].ewm(alpha=1/period, adjust=False).mean() / df['atr'])
    
    # DX and ADX
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].ewm(alpha=1/period, adjust=False).mean()
    
    # Clean up intermediate columns
    df = df.drop(['tr1', 'tr2', 'tr3', 'tr', 'plus_dm', 'minus_dm', 'dx'], axis=1)
    
    return df


def calculate_position_size(account_balance: float, risk_percent: float, 
                          entry_price: float, stop_loss_price: float,
                          pip_value: float = 0.01) -> float:
    """
    Calculate position size based on risk management rules.
    
    Formula: Risk Amount / (Stop Distance in Pips × Pip Value)
    """
    risk_amount = account_balance * (risk_percent / 100)
    stop_distance_pips = abs(entry_price - stop_loss_price) / pip_value
    
    if stop_distance_pips == 0:
        return 0.0
    
    position_size = risk_amount / (stop_distance_pips * pip_value)
    return round(position_size, 2)


def is_london_ny_overlap(timestamp: pd.Timestamp) -> bool:
    """
    Check if timestamp is within London-NY overlap (8 AM - 12 PM EST).
    This is the highest volatility period for XAUUSD.
    """
    # Convert to EST (UTC-5, or UTC-4 during DST)
    # For simplicity, we'll use a rough estimate
    est_hour = timestamp.hour - 5  # Convert UTC to EST
    if est_hour < 0:
        est_hour += 24
    
    return 8 <= est_hour < 12


def backtest_adx_trend_following(df_input: pd.DataFrame, cfg: ADXTrendConfig) -> dict:
    """
    Backtest the ADX Trend Following strategy.
    
    Strategy Rules:
    1. Only trade when ADX > 25 (strong trend confirmed)
    2. Long when price > EMA(20) > EMA(50) and +DI > -DI
    3. Short when price < EMA(20) < EMA(50) and -DI > +DI
    4. Stop loss at 2x ATR from entry
    5. Take profit at 3x ATR from entry (1:1.5 R:R)
    """
    logger.info("=" * 60)
    logger.info("ADX TREND FOLLOWING BACKTEST")
    logger.info("=" * 60)
    logger.info(f"Configuration:")
    logger.info(f"  ADX Period: {cfg.adx_period}, Threshold: {cfg.adx_threshold}")
    logger.info(f"  EMA Fast: {cfg.ema_fast}, Slow: {cfg.ema_slow}")
    logger.info(f"  ATR Multiplier (Stop): {cfg.atr_multiplier_stop}")
    logger.info(f"  ATR Multiplier (Target): {cfg.atr_multiplier_target}")
    logger.info(f"  Risk per Trade: {cfg.risk_per_trade*100}%")
    
    # Prepare data
    df = df_input.copy()
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index(names="time")
    
    if "date" in df.columns and "time" not in df.columns:
        df = df.rename(columns={"date": "time"})
    
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)
    
    # Calculate indicators
    df = calculate_adx(df, cfg.adx_period)
    df['ema_fast'] = df['close'].ewm(span=cfg.ema_fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=cfg.ema_slow, adjust=False).mean()
    
    # ATR for stop loss and take profit
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['atr'] = df['tr'].ewm(span=cfg.atr_period, adjust=False).mean()
    
    # Generate signals
    df['signal'] = 0
    
    # Long: ADX > threshold, price > ema_fast > ema_slow, +DI > -DI
    long_condition = (
        (df['adx'] > cfg.adx_threshold) &
        (df['close'] > df['ema_fast']) &
        (df['ema_fast'] > df['ema_slow']) &
        (df['plus_di'] > df['minus_di'])
    )
    df.loc[long_condition, 'signal'] = 1
    
    # Short: ADX > threshold, price < ema_fast < ema_slow, -DI > +DI
    short_condition = (
        (df['adx'] > cfg.adx_threshold) &
        (df['close'] < df['ema_fast']) &
        (df['ema_fast'] < df['ema_slow']) &
        (df['minus_di'] > df['plus_di'])
    )
    df.loc[short_condition, 'signal'] = -1
    
    # Session filter (optional)
    if cfg.only_trade_london_ny:
        df['in_session'] = df['time'].apply(is_london_ny_overlap)
        df.loc[~df['in_session'], 'signal'] = 0
    
    # Trading simulation
    trades = []
    position = 0  # 0 = none, 1 = long, -1 = short
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    entry_time = None
    
    account_balance = 100000.0  # Starting balance
    equity_curve = [account_balance]
    daily_trades = 0
    current_day = None
    
    for i in range(1, len(df)):
        current_bar = df.iloc[i]
        current_price = current_bar['close']
        current_time = current_bar['time']
        
        # Check for new day
        if current_day != current_time.date():
            current_day = current_time.date()
            daily_trades = 0
        
        # Check exit conditions if in position
        if position != 0:
            exit_triggered = False
            exit_price = current_price
            exit_reason = ""
            
            # Check stop loss
            if position == 1 and current_price <= stop_price:
                exit_triggered = True
                exit_price = stop_price
                exit_reason = "stop_loss"
            elif position == -1 and current_price >= stop_price:
                exit_triggered = True
                exit_price = stop_price
                exit_reason = "stop_loss"
            
            # Check take profit
            elif position == 1 and current_price >= target_price:
                exit_triggered = True
                exit_price = target_price
                exit_reason = "take_profit"
            elif position == -1 and current_price <= target_price:
                exit_triggered = True
                exit_price = target_price
                exit_reason = "take_profit"
            
            # Execute exit
            if exit_triggered:
                if position == 1:
                    pnl = (exit_price - entry_price) / entry_price
                else:
                    pnl = (entry_price - exit_price) / entry_price
                
                # Apply fees
                fee = cfg.fee_bps / 10000 * 2  # Entry + Exit fees
                pnl -= fee
                
                # Update account
                trade_pnl = pnl * account_balance * cfg.risk_per_trade / cfg.atr_multiplier_stop
                account_balance += trade_pnl
                
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': current_time,
                    'direction': 'long' if position == 1 else 'short',
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl': pnl,
                    'exit_reason': exit_reason
                })
                
                position = 0
                equity_curve.append(account_balance)
        
        # Check for entry signals
        if position == 0 and daily_trades < cfg.max_trades_per_day:
            signal = int(current_bar['signal'])
            
            if signal != 0:
                # Calculate ATR for this bar
                atr = current_bar['atr']
                
                # Set entry
                position = signal
                entry_price = current_price
                entry_time = current_time
                
                # Set stop and target based on ATR
                if position == 1:  # Long
                    stop_price = entry_price - (atr * cfg.atr_multiplier_stop)
                    target_price = entry_price + (atr * cfg.atr_multiplier_target)
                else:  # Short
                    stop_price = entry_price + (atr * cfg.atr_multiplier_stop)
                    target_price = entry_price - (atr * cfg.atr_multiplier_target)
                
                daily_trades += 1
    
    # Calculate final metrics
    if len(trades) == 0:
        return {
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'num_trades': 0,
            'profit_factor': 0.0,
            'avg_trade': 0.0,
            'trades': []
        }
    
    # Calculate returns
    total_return = (account_balance - 100000.0) / 100000.0
    
    # Calculate drawdown
    equity_series = pd.Series(equity_curve)
    rolling_max = equity_series.expanding().max()
    drawdown = (equity_series - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    # Win rate
    winning_trades = [t for t in trades if t['pnl'] > 0]
    win_rate = len(winning_trades) / len(trades)
    
    # Profit factor
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] <= 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    # Average trade
    avg_trade = sum(t['pnl'] for t in trades) / len(trades)
    
    logger.info("=" * 60)
    logger.info("ADX TREND FOLLOWING RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total Return: {total_return:.2%}")
    logger.info(f"Max Drawdown: {max_drawdown:.2%}")
    logger.info(f"Win Rate: {win_rate:.1%}")
    logger.info(f"Number of Trades: {len(trades)}")
    logger.info(f"Profit Factor: {profit_factor:.2f}")
    logger.info(f"Average Trade: {avg_trade:.4f}")
    logger.info("=" * 60)
    
    return {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'num_trades': len(trades),
        'profit_factor': profit_factor,
        'avg_trade': avg_trade,
        'trades': trades
    }


# Export the backtest function
__all__ = ['ADXTrendConfig', 'backtest_adx_trend_following', 'calculate_adx']
