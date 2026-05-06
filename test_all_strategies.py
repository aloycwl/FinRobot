#!/usr/bin/env python3
"""
COMPREHENSIVE STRATEGY TEST SUITE

This script tests all new and fixed strategies to ensure they work correctly.

Strategies Tested:
1. ADX Trend Following (NEW)
2. London-NY Breakout (NEW)
3. Fixed Grid (FIXED)
4. Mean Reversion (HFT replacement)
5. Momentum Mean Reversion (RESEARCH)
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("strategy_test")

# Add project path
sys.path.insert(0, '/home/openclaw/FinRobot')

# Import all strategies
from finrobot.strategies.adx_trend import (
    ADXTrendConfig,
    backtest_adx_trend_following
)

from finrobot.strategies.london_ny_breakout import (
    LondonNYBreakoutConfig,
    backtest_london_ny_breakout
)

from finrobot.strategies.fixed_grid import (
    FixedGridConfig,
    backtest_fixed_grid
)

from finrobot.strategies.mean_reversion import (
    MeanReversionConfig,
    backtest_mean_reversion
)

from finrobot.strategies.research_strategies import (
    MomentumMeanReversionConfig,
    backtest_momentum_mean_reversion
)


def generate_test_data(bars=5000, trend_type='random'):
    """Generate synthetic OHLCV data for testing."""
    logger.info(f"Generating {bars} bars of test data ({trend_type})...")
    
    np.random.seed(42)
    
    # Generate timestamps
    start_time = datetime(2024, 1, 1)
    timestamps = [start_time + timedelta(minutes=i) for i in range(bars)]
    
    # Generate price data with some volatility
    price = 2000.0
    opens, highs, lows, closes = [], [], [], []
    volumes = []
    
    for i in range(bars):
        # Add some trend and volatility
        if trend_type == 'uptrend':
            trend = 0.0001
        elif trend_type == 'downtrend':
            trend = -0.0001
        else:
            trend = np.random.choice([-0.00005, 0, 0.00005])
        
        volatility = np.random.normal(0, 0.0005)
        change = trend + volatility
        
        # OHLC
        open_price = price
        close_price = price * (1 + change)
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.0003)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.0003)))
        
        opens.append(open_price)
        highs.append(high_price)
        lows.append(low_price)
        closes.append(close_price)
        volumes.append(np.random.randint(1000, 10000))
        
        price = close_price
    
    df = pd.DataFrame({
        'time': timestamps,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    })
    
    logger.info(f"Generated data: {df['close'].iloc[0]:.2f} -> {df['close'].iloc[-1]:.2f}")
    return df


def test_adx_trend_following():
    """Test ADX Trend Following strategy."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: ADX TREND FOLLOWING")
    logger.info("="*60)
    
    # Generate test data
    df = generate_test_data(bars=3000, trend_type='uptrend')
    
    # Test with default config
    config = ADXTrendConfig(
        adx_threshold=25.0,
        risk_per_trade=0.01
    )
    
    try:
        results = backtest_adx_trend_following(df, config)
        
        logger.info(f"✓ Test PASSED")
        logger.info(f"  Return: {results['total_return']:.2%}")
        logger.info(f"  Win Rate: {results['win_rate']:.1%}")
        logger.info(f"  Trades: {results['num_trades']}")
        logger.info(f"  Max DD: {results['max_drawdown']:.2%}")
        return True
    except Exception as e:
        logger.error(f"✗ Test FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_london_ny_breakout():
    """Test London-NY Breakout strategy."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: LONDON-NY BREAKOUT")
    logger.info("="*60)
    
    # Generate test data (need enough data for session detection)
    df = generate_test_data(bars=5000, trend_type='random')
    
    config = LondonNYBreakoutConfig(
        session_start_hour=8,
        session_end_hour=12,
        risk_per_trade=0.01
    )
    
    try:
        results = backtest_london_ny_breakout(df, config)
        
        logger.info(f"✓ Test PASSED")
        logger.info(f"  Return: {results['total_return']:.2%}")
        logger.info(f"  Win Rate: {results['win_rate']:.1%}")
        logger.info(f"  Trades: {results['num_trades']}")
        logger.info(f"  Max DD: {results['max_drawdown']:.2%}")
        return True
    except Exception as e:
        logger.error(f"✗ Test FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_fixed_grid():
    """Test Fixed Grid strategy."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: FIXED GRID (with risk management)")
    logger.info("="*60)
    
    # Generate sideways/ranging data for grid
    df = generate_test_data(bars=3000, trend_type='random')
    
    config = FixedGridConfig(
        grid_step_pips=2.0,
        take_profit_pips=1.5,
        max_grid_levels=3,
        adx_threshold=25.0,  # Don't trade if ADX > 25
        max_daily_loss_pct=0.02,
        risk_per_grid_level=0.005
    )
    
    try:
        results = backtest_fixed_grid(df, config)
        
        logger.info(f"✓ Test PASSED")
        logger.info(f"  Return: {results['total_return']:.2%}")
        logger.info(f"  Win Rate: {results['win_rate']:.1%}")
        logger.info(f"  Trades: {results['total_trades']}")
        logger.info(f"  Max DD: {results['max_drawdown']:.2%}")
        return True
    except Exception as e:
        logger.error(f"✗ Test FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_mean_reversion():
    """Test Mean Reversion strategy (HFT replacement)."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: MEAN REVERSION (HFT replacement)")
    logger.info("="*60)
    
    # Generate ranging data (best for mean reversion)
    df = generate_test_data(bars=3000, trend_type='random')
    
    config = MeanReversionConfig(
        bb_period=20,
        bb_std_dev=2.0,
        rsi_period=14,
        rsi_overbought=70,
        rsi_oversold=30,
        adx_threshold=20.0,  # Only trade when ADX < 20 (ranging)
        stop_loss_atr_multiplier=1.5,
        take_profit_atr_multiplier=2.0,
        max_hold_bars=20,
        risk_per_trade=0.01
    )
    
    try:
        results = backtest_mean_reversion(df, config)
        
        logger.info(f"✓ Test PASSED")
        logger.info(f"  Return: {results['total_return']:.2%}")
        logger.info(f"  Win Rate: {results['win_rate']:.1%}")
        logger.info(f"  Trades: {results['num_trades']}")
        logger.info(f"  Max DD: {results['max_drawdown']:.2%}")
        return True
    except Exception as e:
        logger.error(f"✗ Test FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_momentum_mean_reversion():
    """Test Momentum Mean Reversion strategy (research-based)."""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: MOMENTUM MEAN REVERSION (research-based)")
    logger.info("="*60)
    
    # Generate ranging data
    df = generate_test_data(bars=3000, trend_type='random')
    
    config = MomentumMeanReversionConfig(
        bb_period=20,
        rsi_period=14,
        rsi_overbought=70,
        rsi_oversold=30,
        momentum_period=5,
        momentum_threshold=0.001,
        adx_max=20,
        use_momentum_filter=True,
        use_mtf_alignment=True,
        stop_loss_atr_multiplier=1.5,
        take_profit_atr_multiplier=2.25,
        max_hold_bars=15,
        risk_per_trade=0.01
    )
    
    try:
        results = backtest_momentum_mean_reversion(df, config)
        
        logger.info(f"✓ Test PASSED")
        logger.info(f"  Return: {results['total_return']:.2%}")
        logger.info(f"  Win Rate: {results['win_rate']:.1%}")
        logger.info(f"  Trades: {results['num_trades']}")
        logger.info(f"  Max DD: {results['max_drawdown']:.2%}")
        return True
    except Exception as e:
        logger.error(f"✗ Test FAILED: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """Run all strategy tests."""
    logger.info("\n" + "="*60)
    logger.info("COMPREHENSIVE STRATEGY TEST SUITE")
    logger.info("="*60)
    
    results = {
        "adx_trend": test_adx_trend_following(),
        "london_ny_breakout": test_london_ny_breakout(),
        "fixed_grid": test_fixed_grid(),
        "mean_reversion": test_mean_reversion(),
        "momentum_mean_reversion": test_momentum_mean_reversion()
    }
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status} - {name}")
    
    logger.info("="*60)
    logger.info(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    logger.info("="*60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
