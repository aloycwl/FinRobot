"""
MEAN REVERSION STRATEGY (HFT Replacement) - Part 2B

This strategy replaces the broken HFT strategy with a working
mean reversion approach based on Bollinger Bands.

Research shows mean reversion works best when:
- ADX < 20 (weak trend/ranging market)
- Price touches outer Bollinger Bands (2+ std dev)
- RSI confirms oversold/overbought conditions
- Volume spike indicates capitulation

Author: FinRobot Research Team
Version: 2.0
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger("mean_reversion")


@dataclass
class MeanReversionConfig:
    """
    Mean Reversion Strategy Configuration
    
    Uses Bollinger Bands with RSI confirmation to identify
    overbought/oversold conditions in ranging markets.
    """
    # Bollinger Band Settings
    bb_period: int = 20
    bb_std_dev: float = 2.0  # 2 standard deviations
    
    # RSI Settings
    rsi_period: int = 14
    rsi_overbought: int = 70
    rsi_oversold: int = 30
    
    # ADX Filter (only trade when ADX < threshold - ranging market)
    adx_period: int = 14
    adx_threshold: float = 20.0  # ADX < 20 = ranging market
    
    # Volume confirmation
    require_volume: bool = True
    volume_ma_period: int = 20
    volume_threshold: float = 1.2  # 1.2x average volume
    
    # Entry/Exit Settings
    entry_at_band_touch: bool = True  # Enter immediately on band touch
    exit_at_middle_band: bool = True  # Exit at middle band (mean reversion)
    
    # Risk Management
    stop_loss_atr_multiplier: float = 1.5  # Stop at 1.5x ATR
    take_profit_atr_multiplier: float = 2.0  # Target at 2x ATR
    max_hold_bars: int = 20  # Max 20 bars hold time
    
    # Position Sizing
    account_balance: float = 100000.0
    base_lot: float = 0.01  # Base lot size
    risk_per_trade: float = 0.01  # 1% risk per trade
    
    # Daily Limits
    max_trades_per_day: int = 5
    max_daily_loss_pct: float = 0.02  # Stop after 2% daily loss
    
    # Execution
    fee_bps: float = 2.0
    
    # Debug
    debug: bool = False


def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: float = 2.0) -> pd.DataFrame:
    """Calculate Bollinger Bands."""
    df['bb_middle'] = df['close'].rolling(window=period).mean()
    bb_std = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * std_dev)
    df['bb_lower'] = df['bb_middle'] - (bb_std * std_dev)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    return df


def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate Relative Strength Index (RSI)."""
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate Average True Range (ATR)."""
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate Average Directional Index (ADX)."""
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
    df = df.drop(['tr1', 'tr2', 'tr3', 'plus_dm', 'minus_dm', 'dx'], axis=1, errors='ignore')
    
    return df


def backtest_mean_reversion(df_input: pd.DataFrame, config: MeanReversionConfig) -> dict:
    """
    Backtest the Mean Reversion strategy using Bollinger Bands and RSI.
    
    Strategy Rules:
    1. Only trade when ADX < 20 (ranging market)
    2. Long when price touches lower BB and RSI < 30
    3. Short when price touches upper BB and RSI > 70
    4. Exit at middle band (mean reversion target)
    5. Stop loss at 1.5x ATR
    """
    logger.info("=" * 60)
    logger.info("MEAN REVERSION STRATEGY BACKTEST")
    logger.info("=" * 60)
    logger.info(f"BB Period: {config.bb_period}, Std Dev: {config.bb_std_dev}")
    logger.info(f"RSI Period: {config.rsi_period}, Overbought: {config.rsi_overbought}, Oversold: {config.rsi_oversold}")
    logger.info(f"ADX Threshold: {config.adx_threshold} (trade when ADX < threshold)")
    logger.info(f"Max Hold Time: {config.max_hold_bars} bars")
    
    # Prepare data
    df = df_input.copy()
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index(names="time")
    
    if "date" in df.columns and "time" not in df.columns:
        df = df.rename(columns={"date": "time"})
    
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)
    
    # Calculate indicators
    df = calculate_bollinger_bands(df, config.bb_period, config.bb_std_dev)
    df = calculate_rsi(df, config.rsi_period)
    df = calculate_adx(df, config.adx_period)
    df = calculate_atr(df, 14)
    
    # Volume calculation
    df['volume_ma'] = df['volume'].rolling(window=config.volume_ma_period).mean()
    df['volume_confirm'] = df['volume'] > (df['volume_ma'] * config.volume_threshold)
    
    # Trading simulation
    trades = []
    position = 0  # 0 = none, 1 = long, -1 = short
    entry_price = 0.0
    stop_price = 0.0
    target_price = 0.0
    entry_time = None
    bars_in_trade = 0
    
    daily_trades = 0
    daily_pnl = 0.0
    current_day = None
    
    account_balance = config.account_balance
    equity_curve = [account_balance]
    
    for i in range(config.bb_period + 10, len(df)):
        current_bar = df.iloc[i]
        current_price = current_bar['close']
        current_time = current_bar['time']
        
        # Check for new day
        if current_day != current_time.date():
            current_day = current_time.date()
            daily_trades = 0
            daily_pnl = 0.0
        
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
            
            # Check take profit (middle band)
            elif position == 1 and current_price >= target_price:
                exit_triggered = True
                exit_price = target_price
                exit_reason = "take_profit"
            elif position == -1 and current_price <= target_price:
                exit_triggered = True
                exit_price = target_price
                exit_reason = "take_profit"
            
            # Check max hold time
            elif bars_in_trade >= config.max_hold_bars:
                exit_triggered = True
                exit_reason = "time_exit"
            
            # Execute exit
            if exit_triggered:
                if position == 1:
                    pnl = (exit_price - entry_price) / entry_price
                else:
                    pnl = (entry_price - exit_price) / entry_price
                
                # Apply fees
                fee = config.fee_bps / 10000 * 2
                pnl -= fee
                
                # Update account
                trade_pnl = pnl * config.base_lot * entry_price
                account_balance += trade_pnl
                daily_pnl += trade_pnl
                
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
        if position == 0 and daily_trades < config.max_trades_per_day:
            # Only trade if ADX < threshold (ranging market)
            if current_bar['adx'] < config.adx_threshold:
                
                # Check volume confirmation
                volume_ok = not config.require_volume or current_bar['volume_confirm']
                
                if volume_ok:
                    # Long signal: Price at lower band + RSI oversold
                    if (current_price <= current_bar['bb_lower'] and 
                        current_bar['rsi'] < config.rsi_oversold):
                        
                        position = 1
                        entry_price = current_price
                        entry_time = current_time
                        bars_in_trade = 0
                        
                        # Set stop and target
                        atr = current_bar['atr']
                        stop_price = entry_price - (atr * config.stop_loss_atr_multiplier)
                        target_price = current_bar['bb_middle']
                        
                        daily_trades += 1
                    
                    # Short signal: Price at upper band + RSI overbought
                    elif (current_price >= current_bar['bb_upper'] and 
                          current_bar['rsi'] > config.rsi_overbought):
                        
                        position = -1
                        entry_price = current_price
                        entry_time = current_time
                        bars_in_trade = 0
                        
                        # Set stop and target
                        atr = current_bar['atr']
                        stop_price = entry_price + (atr * config.stop_loss_atr_multiplier)
                        target_price = current_bar['bb_middle']
                        
                        daily_trades += 1
        
        if position != 0:
            bars_in_trade += 1
    
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
    
    total_return = (account_balance - config.account_balance) / config.account_balance
    
    # Calculate drawdown
    equity_series = pd.Series(equity_curve)
    rolling_max = equity_series.expanding().max()
    drawdown = (equity_series - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    winning_trades = [t for t in trades if t['pnl'] > 0]
    win_rate = len(winning_trades) / len(trades)
    
    gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
    gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] <= 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
    
    avg_trade = sum(t['pnl'] for t in trades) / len(trades)
    
    # Direction breakdown
    long_trades = [t for t in trades if t['direction'] == 'long']
    short_trades = [t for t in trades if t['direction'] == 'short']
    
    # Exit reason breakdown
    exit_reasons = {}
    for t in trades:
        reason = t['exit_reason']
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
    
    logger.info("=" * 60)
    logger.info("MEAN REVERSION RESULTS")
    logger.info("=" * 60)
    logger.info(f"Total Return: {total_return:.2%}")
    logger.info(f"Max Drawdown: {max_drawdown:.2%}")
    logger.info(f"Win Rate: {win_rate:.1%}")
    logger.info(f"Number of Trades: {len(trades)}")
    logger.info(f"Profit Factor: {profit_factor:.2f}")
    logger.info(f"Average Trade: {avg_trade:.4f}")
    logger.info(f"Long Trades: {len(long_trades)}")
    logger.info(f"Short Trades: {len(short_trades)}")
    logger.info("Exit Reasons:")
    for reason, count in exit_reasons.items():
        logger.info(f"  {reason}: {count}")
    logger.info("=" * 60)
    
    return {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'num_trades': len(trades),
        'profit_factor': profit_factor,
        'avg_trade': avg_trade,
        'long_trades': len(long_trades),
        'short_trades': len(short_trades),
        'exit_reasons': exit_reasons,
        'trades': trades
    }


# Export configuration and backtest function
__all__ = ['MeanReversionConfig', 'backtest_mean_reversion']
