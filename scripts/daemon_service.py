#!/usr/bin/env python3
"""
Trading Daemon Service - FIXED VERSION
This version works around the import issues and runs the new strategies
"""

import os
import sys
import json
import time
import signal
import logging
from datetime import datetime
from pathlib import Path

# Setup logging immediately
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/openclaw/FinRobot/trading_daemon.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("daemon")

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

logger.info(f"Python path: {sys.path}")
logger.info(f"Script directory: {script_dir}")
logger.info(f"Parent directory: {parent_dir}")

# Try to import the modules
try:
    from finrobot.utils.data_sources import fetch_candles
    from finrobot.strategies.adx_trend import ADXTrendConfig, backtest_adx_trend_following
    from finrobot.strategies.london_ny_breakout import LondonNYBreakoutConfig, backtest_london_ny_breakout
    from finrobot.strategies.fixed_grid import FixedGridConfig, backtest_fixed_grid
    from finrobot.strategies.mean_reversion import MeanReversionConfig, backtest_mean_reversion
    from finrobot.strategies.research_strategies import MomentumMeanReversionConfig, backtest_momentum_mean_reversion
    
    # Legacy strategies
    from finrobot.strategies.grid import GridConfig, backtest_xauusd_grid
    from finrobot.strategies.backtesting import BacktestConfig, backtest_trend_martingale
    from finrobot.strategies.hft import HFTConfig, backtest_hft
    
    logger.info("✓ All imports successful")
    IMPORTS_WORKING = True
except Exception as e:
    logger.error(f"✗ Import error: {e}")
    logger.error(traceback.format_exc())
    IMPORTS_WORKING = False

# State files
STATE_FILE = "/home/openclaw/FinRobot/daemon_state.json"
PID_FILE = "/home/openclaw/FinRobot/daemon.pid"
RESULTS_FILE = "/home/openclaw/FinRobot/backtest_results.jsonl"

# Configuration
SLEEP_INTERVAL = 30  # Sleep interval in seconds

class DaemonState:
    def __init__(self):
        self.running = False
        self.cycle_count = 0
        self.best_results = {}
        self.load()
    
    def load(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                    self.running = data.get('running', False)
                    self.cycle_count = data.get('cycle_count', 0)
                    self.best_results = data.get('best_results', {})
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
    
    def save(self):
        data = {
            'running': self.running,
            'cycle_count': self.cycle_count,
            'best_results': self.best_results,
            'timestamp': datetime.now().isoformat()
        }
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

def log_result(result):
    """Log a backtest result."""
    try:
        with open(RESULTS_FILE, 'a') as f:
            f.write(json.dumps(result, default=str) + '\n')
    except Exception as e:
        logger.error(f"Failed to log result: {e}")

def generate_random_params(strategy):
    """Generate random parameters for a strategy."""
    import random
    
    if strategy == "adx_trend":
        return {
            "adx_period": random.choice([10, 14, 20]),
            "adx_threshold": random.choice([20.0, 25.0, 30.0]),
            "ema_fast": random.choice([15, 20, 25]),
            "ema_slow": random.choice([40, 50, 60]),
            "atr_multiplier_stop": random.choice([1.5, 2.0, 2.5]),
            "atr_multiplier_target": random.choice([2.5, 3.0, 3.5]),
            "risk_per_trade": random.choice([0.005, 0.01, 0.015])
        }
    elif strategy == "london_ny_breakout":
        return {
            "session_start_hour": random.choice([7, 8, 9]),
            "session_end_hour": random.choice([11, 12, 13]),
            "lookback_hours": random.choice([2, 4, 6]),
            "breakout_threshold_pct": random.choice([0.0005, 0.001, 0.002]),
            "stop_loss_atr_multiplier": random.choice([1.0, 1.5, 2.0]),
            "take_profit_atr_multiplier": random.choice([2.0, 2.5, 3.0])
        }
    elif strategy == "mean_reversion":
        return {
            "bb_period": random.choice([15, 20, 25]),
            "bb_std_dev": random.choice([1.5, 2.0, 2.5]),
            "rsi_period": random.choice([10, 14, 21]),
            "rsi_overbought": random.choice([65, 70, 75]),
            "rsi_oversold": random.choice([25, 30, 35]),
            "adx_threshold": random.choice([15.0, 20.0, 25.0]),
            "stop_loss_atr_multiplier": random.choice([1.0, 1.5, 2.0]),
            "take_profit_atr_multiplier": random.choice([1.5, 2.0, 2.5])
        }
    elif strategy == "grid":
        return {
            "grid_step_pips": random.choice([0.5, 1.0, 2.0, 3.0, 5.0]),
            "take_profit_pips": random.choice([0.3, 0.5, 1.0, 1.5, 2.0]),
            "trend_ema_fast": random.choice([3, 5, 8, 12, 21]),
            "trend_ema_slow": random.choice([8, 15, 21, 34, 55]),
            "max_grid_levels": random.choice([2, 4, 6, 8, 12]),
            "base_lot": random.choice([0.005, 0.01, 0.02, 0.05]),
            "fee_bps": random.choice([1.0, 2.0, 3.0])
        }
    elif strategy == "martingale":
        return {
            "multiplier": random.choice([1.25, 1.5, 1.75, 2.0, 2.25, 2.5]),
            "base_lot": random.choice([0.005, 0.01, 0.02, 0.03]),
            "max_steps": random.choice([2, 3, 4, 5, 6]),
            "ema_fast": random.choice([3, 5, 8]),
            "ema_slow": random.choice([12, 20, 34]),
            "fee_bps": random.choice([1.0, 2.0, 3.0])
        }
    else:
        return {}

def run_backtest_cycle(state):
    """Run one backtest cycle."""
    import traceback
    
    state.cycle_count += 1
    cycle_num = state.cycle_count
    
    logger.info(f"{'='*60}")
    logger.info(f"BACKTEST CYCLE #{cycle_num}")
    logger.info(f"{'='*60}")
    
    # Load data
    try:
        df = fetch_candles(limit=10000)
        logger.info(f"Loaded {len(df)} bars")
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return False
    
    # Test new strategies
    strategies_to_test = []
    
    if IMPORTS_WORKING:
        strategies_to_test = [
            ("adx_trend", lambda df, params: backtest_adx_trend_following(df, ADXTrendConfig(**params))),
            ("london_ny_breakout", lambda df, params: backtest_london_ny_breakout(df, LondonNYBreakoutConfig(**params))),
            ("mean_reversion", lambda df, params: backtest_mean_reversion(df, MeanReversionConfig(**params))),
            ("grid", lambda df, params: backtest_xauusd_grid(df, GridConfig(**params))),
            ("martingale", lambda df, params: backtest_trend_martingale(df, BacktestConfig(**params))),
        ]
    else:
        logger.error("Imports not working, cannot run strategies")
        return False
    
    # Run each strategy
    for strategy_name, backtest_func in strategies_to_test:
        try:
            params = generate_random_params(strategy_name)
            result = backtest_func(df, params)
            
            # Log result
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "strategy": strategy_name,
                "parameters": params,
                "performance": result,
                "cycle": cycle_num
            }
            log_result(log_entry)
            
            # Update best results
            perf_key = "total_return"
            if perf_key in result:
                current_best = state.best_results.get(strategy_name, {}).get(perf_key, -999)
                if result[perf_key] > current_best:
                    state.best_results[strategy_name] = result
                    logger.info(f"★ NEW BEST for {strategy_name}: {result[perf_key]:.2%}")
            
            # Print summary
            if "total_return" in result:
                ret = result.get('total_return', 0)
                wr = result.get('win_rate', 0)
                trades = result.get('num_trades', result.get('total_trades', 0))
                logger.info(f"  [{strategy_name[:3].upper()}] {ret:+.2f}% | WR:{wr:.1%} | T:{trades}")
                
        except Exception as e:
            logger.error(f"Failed to run {strategy_name}: {e}")
            logger.error(traceback.format_exc())
    
    # Save state
    state.save()
    
    # Cleanup
    del df
    gc.collect()
    
    return True

def main():
    """Main daemon loop."""
    global SLEEP_INTERVAL
    import argparse
    
    parser = argparse.ArgumentParser(description="Trading Daemon Service")
    parser.add_argument("--cycles", type=int, default=None, help="Number of cycles to run")
    parser.add_argument("--interval", type=int, default=SLEEP_INTERVAL, help="Sleep interval in seconds")
    args = parser.parse_args()
    
    SLEEP_INTERVAL = args.interval
    
    logger.info("="*60)
    logger.info("TRADING DAEMON STARTING")
    logger.info("="*60)
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Sleep interval: {SLEEP_INTERVAL}s")
    logger.info(f"Imports working: {IMPORTS_WORKING}")
    
    # Initialize state
    state = DaemonState()
    state.running = True
    state.save()
    
    # Write PID file
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    
    cycle_count = 0
    
    try:
        while state.running:
            cycle_count += 1
            
            # Run backtest cycle
            success = run_backtest_cycle(state)
            
            if not success:
                logger.error("Cycle failed, continuing...")
            
            # Check if we should stop
            if args.cycles and cycle_count >= args.cycles:
                logger.info(f"Reached cycle limit ({args.cycles}), stopping.")
                break
            
            # Sleep
            logger.info(f"Sleeping for {SLEEP_INTERVAL}s...")
            time.sleep(SLEEP_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Cleanup
        state.running = False
        state.save()
        
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        
        logger.info("="*60)
        logger.info("TRADING DAEMON STOPPED")
        logger.info("="*60)

if __name__ == "__main__":
    main()
