#!/usr/bin/env python3
"""
Continuous Backtesting System for XAUUSD 1m Data

This script runs continuous backtests on local XAUUSD 1m data,
optimizing parameters and logging results. No live trading.
"""

from __future__ import annotations

import os
import sys
import time
import json
import logging
import itertools
import random
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path

import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from finrobot.config import settings
from finrobot.data_sources import fetch_candles
from finrobot.grid import GridConfig, backtest_xauusd_grid
from finrobot.backtesting import BacktestConfig, backtest_trend_martingale
from finrobot.hft import HFTConfig, backtest_hft


# ============================================================================
# Configuration
# ============================================================================

LOG_DIR = Path("/home/openclaw/FinRobot/backtest_logs")
LOG_DIR.mkdir(exist_ok=True)

RESULTS_FILE = LOG_DIR / "backtest_results.jsonl"
BEST_PARAMS_FILE = LOG_DIR / "best_parameters.json"
SUMMARY_FILE = LOG_DIR / "summary.txt"

# How often to run full parameter sweep (in cycles)
SWEEP_INTERVAL = 10

# Sleep between cycles (seconds)
CYCLE_SLEEP = 2


# ============================================================================
# Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "backtest_engine.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("backtest_engine")


# ============================================================================
# Parameter Space Definitions
# ============================================================================

PARAMETER_SPACE = {
    "grid": {
        "grid_step_pips": [0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0],
        "take_profit_pips": [0.3, 0.5, 1.0, 1.5, 2.0, 3.0],
        "trend_ema_fast": [3, 5, 8, 12, 21],
        "trend_ema_slow": [8, 15, 21, 34, 55],
        "max_grid_levels": [2, 4, 6, 8, 12],
        "base_lot": [0.005, 0.01, 0.02, 0.05],
        "fee_bps": [1.0, 2.0, 3.0],
        "pip_value": [0.01]
    },
    "martingale": {
        "multiplier": [1.25, 1.5, 1.75, 2.0, 2.25, 2.5],
        "base_lot": [0.005, 0.01, 0.02, 0.03],
        "max_steps": [2, 3, 4, 5, 6],
        "ema_fast": [3, 5, 8],
        "ema_slow": [12, 20, 34],
        "fee_bps": [1.0, 2.0, 3.0]
    },
    "hft": {
        "tick_threshold": [0.02, 0.05, 0.08, 0.12],
        "volume_filter": [10, 25, 50, 100],
        "latency_ms": [50, 100, 200],
        "spread_limit": [0.01, 0.02, 0.03],
        "fast_window": [3, 5, 8],
        "slow_window": [12, 20, 34],
        "fee_bps": [1.0, 2.0, 3.0],
        "risk_per_trade": [0.002, 0.005, 0.01]
    }
}


# ============================================================================
# Results Tracking
# ============================================================================

@dataclass
class BacktestResult:
    timestamp: str
    strategy: str
    parameters: Dict[str, Any]
    performance: Dict[str, float]
    data_bars: int
    cycle: int
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "strategy": self.strategy,
            "parameters": self.parameters,
            "performance": self.performance,
            "data_bars": self.data_bars,
            "cycle": self.cycle
        }


class ResultsTracker:
    def __init__(self):
        self.best_results: Dict[str, BacktestResult] = {}
        self.cycle_count = 0
        self.total_tests = 0
        self.load_best_params()
        
    def load_best_params(self):
        """Load previously saved best parameters."""
        if BEST_PARAMS_FILE.exists():
            try:
                with open(BEST_PARAMS_FILE, 'r') as f:
                    data = json.load(f)
                    for strategy, result_data in data.items():
                        self.best_results[strategy] = BacktestResult(**result_data)
                logger.info(f"Loaded {len(self.best_results)} best parameter sets")
            except Exception as e:
                logger.warning(f"Could not load best parameters: {e}")
    
    def save_best_params(self):
        """Save best parameters to file."""
        data = {}
        for strategy, result in self.best_results.items():
            data[strategy] = result.to_dict()
        with open(BEST_PARAMS_FILE, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def log_result(self, result: BacktestResult):
        """Log a result to the results file."""
        self.total_tests += 1
        with open(RESULTS_FILE, 'a') as f:
            f.write(json.dumps(result.to_dict(), default=str) + '\n')
    
    def update_best(self, result: BacktestResult) -> bool:
        """Update best result if this one is better."""
        strategy = result.strategy
        
        # Skip if performance has error
        if 'error' in result.performance:
            return False
        
        current_best = self.best_results.get(strategy)
        
        if current_best is None:
            self.best_results[strategy] = result
            self.save_best_params()
            return True
        
        # Compare by total return
        current_return = current_best.performance.get('total_return', -999)
        new_return = result.performance.get('total_return', -999)
        
        if new_return > current_return:
            self.best_results[strategy] = result
            self.save_best_params()
            return True
        
        return False
    
    def print_summary(self):
        """Print concise summary of best results."""
        logger.info("-" * 80)
        logger.info(f"SUMMARY | Cycle {self.cycle_count} | Total Tests: {self.total_tests}")

        for strategy, result in self.best_results.items():
            perf = result.performance
            strat_letter = strategy[:1].upper()
            logger.info(
                f"  [{strat_letter}] Best: {perf.get('total_return', 0):+.2f}% | "
                f"WR:{perf.get('win_rate', 0):.1f}% | "
                f"DD:{perf.get('max_drawdown', 0):.2f}% | "
                f"T:{perf.get('total_trades', perf.get('num_trades', 0))}"
            )

        logger.info("-" * 80)


# ============================================================================
# Main Backtest Engine
# ============================================================================

class BacktestEngine:
    def __init__(self):
        self.tracker = ResultsTracker()
        self.running = True
        self.current_params = {
            "grid": GridConfig(),
            "martingale": BacktestConfig(),
            "hft": HFTConfig()
        }
        
    def generate_random_params(self, strategy: str) -> dict:
        """Generate random parameters from the parameter space."""
        params = {}
        for key, values in PARAMETER_SPACE[strategy].items():
            params[key] = random.choice(values)
        return params
    
    def run_single_backtest(self, strategy: str, params: dict, df: pd.DataFrame) -> Optional[BacktestResult]:
        """Run a single backtest with given parameters."""
        try:
            if strategy == "grid":
                cfg = GridConfig(**params)
                result = backtest_xauusd_grid(df, cfg)
            elif strategy == "martingale":
                cfg = BacktestConfig(**params)
                result = backtest_trend_martingale(df, cfg)
            elif strategy == "hft":
                cfg = HFTConfig(**params)
                result = backtest_hft(df, cfg)
            else:
                return None
            
            return BacktestResult(
                timestamp=datetime.utcnow().isoformat(),
                strategy=strategy,
                parameters=params,
                performance=result,
                data_bars=len(df),
                cycle=self.tracker.cycle_count
            )
            
        except Exception as e:
            logger.error(f"Backtest failed for {strategy}: {e}")
            return BacktestResult(
                timestamp=datetime.utcnow().isoformat(),
                strategy=strategy,
                parameters=params,
                performance={"error": str(e)},
                data_bars=len(df),
                cycle=self.tracker.cycle_count
            )
    
    def run_cycle(self, full_sweep: bool = False):
        """Run one backtest cycle."""
        self.tracker.cycle_count += 1
        cycle_num = self.tracker.cycle_count

        # Only log cycle header every 10 cycles to reduce noise
        if cycle_num % 10 == 1 or full_sweep:
            logger.info(f"{'='*60}")
            logger.info(f"BACKTEST CYCLE #{cycle_num}")
            logger.info(f"{'='*60}")
        
        # Load data
        try:
            df = fetch_candles(limit=10000)
            if cycle_num % 10 == 1 or full_sweep:
                logger.info(f"Loaded {len(df)} bars | Progress: {cycle_num}/10000 ({cycle_num/100:.1f}%)")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return

        # Determine how many parameter combinations to test
        if full_sweep:
            tests_per_strategy = 10
            if cycle_num % 10 == 1:
                logger.info("Running FULL PARAMETER SWEEP")
        else:
            tests_per_strategy = 3

        # Track best results in this cycle
        cycle_best = {"strategy": "-", "return": -999, "win_rate": 0}
        cycle_results = []

        # Run backtests for each strategy
        for strategy in ["grid", "martingale", "hft"]:
            for i in range(tests_per_strategy):
                # Generate parameters
                if i == 0:
                    if strategy == "grid":
                        params = asdict(GridConfig())
                    elif strategy == "martingale":
                        params = asdict(BacktestConfig())
                    else:
                        params = asdict(HFTConfig())
                else:
                    params = self.generate_random_params(strategy)

                # Run backtest
                result = self.run_single_backtest(strategy, params, df)

                if result:
                    self.tracker.log_result(result)
                    is_best = self.tracker.update_best(result)

                    perf = result.performance
                    if 'error' not in perf:
                        ret = perf.get('total_return', 0)
                        wr = perf.get('win_rate', 0)
                        trades = perf.get('total_trades', perf.get('num_trades', 0))

                        # Track cycle best
                        if ret > cycle_best["return"]:
                            cycle_best = {
                                "strategy": strategy[:1].upper(),
                                "return": ret,
                                "win_rate": wr
                            }

                        # Log individual test only if it's the best or has errors
                        if is_best or cycle_num % 50 == 0:
                            best_marker = " ★BEST" if is_best else ""
                            logger.info(f"  [{strategy[:1].upper()}] Test {i+1}: {ret:+.2%} WR:{wr:.1f}% T:{trades}{best_marker}")

        # Only print summary every 10 cycles or on full sweep
        if cycle_num % 10 == 0 or full_sweep:
            self.tracker.print_summary()
    
    def run(self, cycles: Optional[int] = None):
        """Run the backtest engine continuously."""
        logger.info("="*60)
        logger.info("CONTINUOUS BACKTEST ENGINE STARTED")
        logger.info("="*60)
        logger.info(f"Data: XAUUSD 1m from local CSV")
        logger.info(f"Strategies: Grid, Martingale, HFT")
        logger.info(f"Results logged to: {LOG_DIR}")
        logger.info("="*60)
        
        try:
            cycle_count = 0
            while self.running:
                cycle_count += 1
                
                # Run full sweep every N cycles
                full_sweep = (cycle_count % SWEEP_INTERVAL) == 0
                
                self.run_cycle(full_sweep=full_sweep)
                
                # Check if we've reached max cycles
                if cycles is not None and cycle_count >= cycles:
                    logger.info(f"Reached max cycles ({cycles}), stopping.")
                    break
                
                # Sleep before next cycle
                time.sleep(CYCLE_SLEEP)
                
        except KeyboardInterrupt:
            logger.info("\nReceived interrupt signal, shutting down...")
        finally:
            self.running = False
            logger.info("Backtest engine stopped.")
            self.tracker.print_summary()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Continuous Backtesting for XAUUSD")
    parser.add_argument("--cycles", type=int, default=None, help="Number of cycles to run (default: infinite)")
    parser.add_argument("--sleep", type=int, default=2, help="Seconds to sleep between cycles")
    args = parser.parse_args()
    
    global CYCLE_SLEEP
    CYCLE_SLEEP = args.sleep
    
    engine = BacktestEngine()
    engine.run(cycles=args.cycles)


if __name__ == "__main__":
    main()
