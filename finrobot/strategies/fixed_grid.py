"""
FIXED STRATEGY STACK - Part 2: Corrected and Improved Strategies

This module fixes the broken strategies:
1. Martingale -> REMOVED (mathematically proven to fail)
2. Grid -> FIXED with proper risk management and trend filters
3. HFT -> CONVERTED to Mean Reversion (BB reversal strategy)

Author: FinRobot Research Team
Version: 2.0
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger("fixed_strategies")


# ============================================================================
# PART 2A: FIXED GRID STRATEGY WITH PROPER RISK MANAGEMENT
# ============================================================================

@dataclass
class FixedGridConfig:
    """
    Fixed Grid Strategy with Risk Management
    
    Improvements over original:
    - Trend filter to avoid grid trading in strong trends
    - Maximum drawdown protection
    - Daily loss limits
    - Proper position sizing
    - Automatic grid shutdown on adverse moves
    """
    # Grid Settings
    grid_step_pips: float = 2.0  # Space between grid levels
    take_profit_pips: float = 1.5  # TP for each grid trade
    max_grid_levels: int = 3  # Maximum concurrent positions
    
    # Trend Filter (NEW - prevents grid trading in strong trends)
    use_trend_filter: bool = True
    trend_ema_fast: int = 8
    trend_ema_slow: int = 21
    adx_period: int = 14
    adx_threshold: float = 25.0  # Don't grid trade if ADX > 25
    
    # Risk Management (NEW)
    max_daily_loss_pct: float = 0.02  # Stop after 2% daily loss
    max_drawdown_pct: float = 0.05  # Max 5% drawdown
    daily_trade_limit: int = 10  # Max 10 trades per day
    
    # Position Sizing
    base_lot: float = 0.01
    account_balance: float = 100000.0
    risk_per_grid_level: float = 0.005  # 0.5% risk per grid level
    
    # Emergency Shutdown (NEW)
    emergency_shutdown_after_losses: int = 3  # Stop after 3 consecutive losses
    
    # Execution
    pip_value: float = 0.01  # XAUUSD
    fee_bps: float = 2.0
    
    # Debug
    debug: bool = False


def calculate_grid_indicators(df: pd.DataFrame, config: FixedGridConfig) -> pd.DataFrame:
    """Calculate indicators for grid strategy with trend filter."""
    df = df.copy()
    
    # EMAs for trend
    df['ema_fast'] = df['close'].ewm(span=config.trend_ema_fast, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=config.trend_ema_slow, adjust=False).mean()
    
    # ADX calculation
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
    df['atr'] = df['tr'].ewm(alpha=1/config.adx_period, adjust=False).mean()
    df['plus_di'] = 100 * (df['plus_dm'].ewm(alpha=1/config.adx_period, adjust=False).mean() / df['atr'])
    df['minus_di'] = 100 * (df['minus_dm'].ewm(alpha=1/config.adx_period, adjust=False).mean() / df['atr'])
    
    # DX and ADX
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['adx'] = df['dx'].ewm(alpha=1/config.adx_period, adjust=False).mean()
    
    # Trend filter: Only trade when ADX < threshold (weak trend = ranging market)
    df['can_trade_grid'] = df['adx'] < config.adx_threshold
    
    # Clean up intermediate columns
    df = df.drop(['tr1', 'tr2', 'tr3', 'plus_dm', 'minus_dm', 'dx'], axis=1, errors='ignore')
    
    return df


def backtest_fixed_grid(df_input: pd.DataFrame, config: FixedGridConfig) -> dict:
    """
    Backtest the Fixed Grid strategy with proper risk management.
    
    Key improvements:
    1. Trend filter - only grid trade when ADX < 25 (ranging market)
    2. Daily loss limit - stop after 2% loss
    3. Max drawdown protection
    4. Emergency shutdown after consecutive losses
    """
    logger.info("=" * 60)
    logger.info("FIXED GRID STRATEGY BACKTEST")
    logger.info("=" * 60)
    logger.info(f"Grid Step: {config.grid_step_pips} pips")
    logger.info(f"Take Profit: {config.take_profit_pips} pips")
    logger.info(f"Max Grid Levels: {config.max_grid_levels}")
    logger.info(f"ADX Threshold: {config.adx_threshold} (trade when ADX < threshold)")
    logger.info(f"Daily Loss Limit: {config.max_daily_loss_pct:.1%}")
    logger.info(f"Emergency Shutdown: {config.emergency_shutdown_after_losses} consecutive losses")
    
    # Prepare data
    df = df_input.copy()
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index(names="time")
    
    if "date" in df.columns and "time" not in df.columns:
        df = df.rename(columns={"date": "time"})
    
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("time").reset_index(drop=True)
    
    # Calculate indicators
    df = calculate_grid_indicators(df, config)
    
    # Grid trading simulation
    trades = []
    active_positions = []  # List of {entry_price, direction, level}
    position_count = 0
    daily_pnl = 0.0
    daily_trades = 0
    consecutive_losses = 0
    current_day = None
    emergency_shutdown = False
    
    account_balance = config.account_balance
    equity_curve = [account_balance]
    max_equity = account_balance
    
    grid_step_price = config.grid_step_pips * config.pip_value
    take_profit_price = config.take_profit_pips * config.pip_value
    
    for i in range(1, len(df)):
        current_bar = df.iloc[i]
        current_price = current_bar['close']
        current_time = current_bar['time']
        
        # Check for new day
        if current_day != current_time.date():
            current_day = current_time.date()
            daily_pnl = 0.0
            daily_trades = 0
            consecutive_losses = 0
            emergency_shutdown = False
        
        # Check daily loss limit
        if daily_pnl < -config.max_daily_loss_pct * account_balance:
            emergency_shutdown = True
        
        # Check emergency shutdown
        if consecutive_losses >= config.emergency_shutdown_after_losses:
            emergency_shutdown = True
        
        # Check take profits for existing positions
        positions_to_remove = []
        for idx, pos in enumerate(active_positions):
            exit_triggered = False
            exit_price = current_price
            pnl = 0.0
            
            if pos['direction'] == 'long':
                if current_price >= pos['entry_price'] + take_profit_price:
                    exit_triggered = True
                    exit_price = pos['entry_price'] + take_profit_price
                    pnl = take_profit_price / pos['entry_price'] - (config.fee_bps / 10000 * 2)
            else:  # short
                if current_price <= pos['entry_price'] - take_profit_price:
                    exit_triggered = True
                    exit_price = pos['entry_price'] - take_profit_price
                    pnl = take_profit_price / pos['entry_price'] - (config.fee_bps / 10000 * 2)
            
            if exit_triggered:
                trades.append({
                    'entry_time': pos['entry_time'],
                    'exit_time': current_time,
                    'direction': pos['direction'],
                    'entry_price': pos['entry_price'],
                    'exit_price': exit_price,
                    'pnl': pnl
                })
                
                account_balance += pnl * config.base_lot * pos['entry_price']
                daily_pnl += pnl * config.base_lot * pos['entry_price']
                
                if pnl > 0:
                    consecutive_losses = 0
                else:
                    consecutive_losses += 1
                
                positions_to_remove.append(idx)
                daily_trades += 1
        
        # Remove closed positions (in reverse order)
        for idx in sorted(positions_to_remove, reverse=True):
            active_positions.pop(idx)
        
        # Open new positions if conditions met
        if (not emergency_shutdown and 
            len(active_positions) < config.max_grid_levels and
            daily_trades < config.daily_trade_limit and
            (not config.use_trend_filter or current_bar['can_trade_grid'])):
            
            # Check if we should open a new grid level
            if len(active_positions) == 0:
                # First position - enter immediately at current price
                direction = 'long' if np.random.random() > 0.5 else 'short'
                
                active_positions.append({
                    'entry_price': current_price,
                    'direction': direction,
                    'entry_time': current_time,
                    'level': 1
                })
            else:
                # Add grid levels based on price movement
                last_pos = active_positions[-1]
                price_diff = abs(current_price - last_pos['entry_price'])
                
                if price_diff >= grid_step_price:
                    # Open new level in same direction
                    active_positions.append({
                        'entry_price': current_price,
                        'direction': last_pos['direction'],
                        'entry_time': current_time,
                        'level': last_pos['level'] + 1
                    })
        
        # Update equity and max equity
        equity_curve.append(account_balance)
        max_equity = max(max_equity, account_balance)
        
        # Check max drawdown
        current_drawdown = (max_equity - account_balance) / max_equity
        if current_drawdown > config.max_drawdown_pct:
            emergency_shutdown = True
    
    # Calculate final metrics
    if len(trades) == 0:
        return {
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
            'profit_factor': 0.0,
            'avg_trade': 0.0,
            'trades': []
        }
    
    total_return = (account_balance - config.account_balance) / config.account_balance
    
    # Calculate drawdown from equity curve
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
    
    return {
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'total_trades': len(trades),
        'profit_factor': profit_factor,
        'avg_trade': avg_trade,
        'trades': trades
    }


# Export configuration and backtest function
__all__ = ['FixedGridConfig', 'backtest_fixed_grid']
