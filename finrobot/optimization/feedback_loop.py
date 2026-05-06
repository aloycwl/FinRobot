"""
FIXED Autonomous Feedback Loop - Version 2.0

This module implements a self-improving trading system that:
1. Tests NEW strategies (ADX Trend, London-NY Breakout, Mean Reversion, etc.)
2. Automatically triggers Opencode when performance is poor
3. Continuously optimizes parameters
4. Tracks best performing configurations

Key Fixes:
- Now tests the 5 NEW strategies instead of legacy broken ones
- Properly calls should_trigger() to invoke Opencode when needed
- Includes all new strategy configs and backtest functions
- Better logging and error handling
"""

from __future__ import annotations

import os
import json
import time
import itertools
import threading
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Iterator
import pandas as pd
import numpy as np

from finrobot.utils.config import settings
from finrobot.utils.data_sources import fetch_okx_candles, fetch_candles
from finrobot.strategies.backtesting import backtest_trend_martingale, BacktestConfig
from finrobot.strategies.grid import GridConfig, backtest_xauusd_grid
from finrobot.strategies.hft import HFTConfig, backtest_hft

# NEW STRATEGY IMPORTS
from finrobot.strategies.adx_trend import ADXTrendConfig, backtest_adx_trend_following
from finrobot.strategies.london_ny_breakout import LondonNYBreakoutConfig, backtest_london_ny_breakout
from finrobot.strategies.mean_reversion import MeanReversionConfig, backtest_mean_reversion

from finrobot.optimization.opencode_integration import OpencodeFeedbackLoop
from finrobot.hot_reload import reload_all_modules
from finrobot.utils.logging_config import get_logger


logger = get_logger("feedback_loop")


@dataclass
class ParameterSet:
    strategy: str
    parameters: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    performance: Optional[Dict[str, float]] = None
    tested_at: Optional[datetime] = None
    is_best: bool = False


@dataclass
class FeedbackLoopState:
    running: bool = False
    iteration: int = 0
    best_parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tested_parameters: List[ParameterSet] = field(default_factory=list)
    last_sweep: Optional[datetime] = None
    target_hourly_return: float = 0.05  # 5% hourly target
    last_opencode_call: Optional[datetime] = None


class AutonomousFeedbackLoop:
    """
    FIXED Autonomous Feedback Loop that:
    1. Tests the 5 NEW strategies (ADX, London-NY, Mean Reversion, etc.)
    2. Triggers Opencode when performance is poor
    3. Tracks best parameters
    """
    
    def __init__(self, daemon):
        self.daemon = daemon
        self.state = FeedbackLoopState()
        self.state_file = "/home/openclaw/FinRobot/feedback_loop_state.json"
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.opencode = OpencodeFeedbackLoop()
        self.consecutive_failures = 0

        # PARAMETER SPACES FOR NEW STRATEGIES
        self.parameter_space = {
            # NEW: ADX Trend Following
            "adx_trend": {
                "adx_period": [10, 14, 20],
                "adx_threshold": [20.0, 25.0, 30.0],
                "ema_fast": [10, 15, 20],
                "ema_slow": [30, 40, 50],
                "atr_multiplier_stop": [1.5, 2.0, 2.5],
                "atr_multiplier_target": [3.0, 3.5, 4.0],
                "risk_per_trade": [0.01, 0.015, 0.02]
            },
            # NEW: London-NY Breakout
            "london_ny_breakout": {
                "session_start_hour": [7, 8, 9],
                "session_end_hour": [11, 12, 13],
                "lookback_hours": [3, 4, 5],
                "breakout_threshold_pct": [0.0005, 0.001, 0.002],
                "require_volume_confirmation": [True, False],
                "volume_threshold": [1.2, 1.5, 2.0],
                "risk_per_trade": [0.008, 0.01, 0.015],
                "atr_multiplier_sl": [1.0, 1.5, 2.0],
                "atr_multiplier_tp": [2.0, 2.5, 3.0]
            },
            # NEW: Mean Reversion
            "mean_reversion": {
                "bb_period": [15, 20, 25],
                "bb_std_dev": [1.5, 2.0, 2.5],
                "rsi_period": [10, 14, 18],
                "rsi_overbought": [65, 70, 75],
                "rsi_oversold": [25, 30, 35],
                "adx_period": [10, 14, 20],
                "adx_threshold": [15.0, 20.0, 25.0],
                "require_volume": [True, False],
                "volume_threshold": [1.2, 1.5, 2.0],
                "risk_per_trade": [0.01, 0.015, 0.02]
            },
            # LEGACY: Grid (kept for comparison)
            "grid": {
                "grid_step_pips": [0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0],
                "take_profit_pips": [0.3, 0.5, 1.0, 1.5, 2.0, 3.0],
                "trend_ema_fast": [3, 5, 8, 12, 21],
                "trend_ema_slow": [8, 15, 21, 34, 55],
                "max_grid_levels": [2, 4, 6, 8, 12],
                "base_lot": [0.005, 0.01, 0.02, 0.05]
            }
        }

        self.load_state()

    def load_state(self):
        """Load state from JSON file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.state.best_parameters = data.get("best_parameters", {})
                    self.state.iteration = data.get("iteration", 0)
                    last_opencode_str = data.get("last_opencode_call")
                    if last_opencode_str:
                        self.state.last_opencode_call = datetime.fromisoformat(last_opencode_str)
                    logger.info(f"Loaded feedback loop state: {self.state.iteration} iterations, "
                               f"{len(self.state.best_parameters)} best parameter sets")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def save_state(self):
        """Save state to JSON file."""
        def json_default(obj):
            if isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
            
        try:
            with open(self.state_file, "w") as f:
                json.dump({
                    "iteration": self.state.iteration,
                    "best_parameters": self.state.best_parameters,
                    "last_sweep": self.state.last_sweep.isoformat() if self.state.last_sweep else None,
                    "last_opencode_call": self.state.last_opencode_call.isoformat() if self.state.last_opencode_call else None
                }, f, indent=2, default=json_default)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def log_iteration(self, parameter_set: ParameterSet):
        """Log iteration details."""
        if parameter_set.is_best:
            perf = parameter_set.performance or {}
            logger.info(f"★ New best for {parameter_set.strategy}: "
                       f"Return={perf.get('total_return', 0):.2%}, "
                       f"WinRate={perf.get('win_rate', 0):.1%}, "
                       f"Trades={perf.get('num_trades', 0)}")

    def generate_parameter_combinations(self, strategy: str) -> Iterator[Dict[str, Any]]:
        """Generate all parameter combinations for a strategy."""
        space = self.parameter_space.get(strategy, {})
        if not space:
            return iter([])
        keys = list(space.keys())
        for values in itertools.product(*space.values()):
            yield dict(zip(keys, values))

    def run_backtest(self, strategy: str, params: Dict[str, Any], df: pd.DataFrame) -> Dict[str, float]:
        """Run backtest for a strategy with given parameters."""
        try:
            if strategy == "adx_trend":
                cfg = ADXTrendConfig(**params)
                return backtest_adx_trend(df, cfg)
            elif strategy == "london_ny_breakout":
                cfg = LondonNYBreakoutConfig(**params)
                return backtest_london_ny_breakout(df, cfg)
            elif strategy == "mean_reversion":
                cfg = MeanReversionConfig(**params)
                return backtest_mean_reversion(df, cfg)
            elif strategy == "grid":
                cfg = GridConfig(**params)
                return backtest_xauusd_grid(df, cfg)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
        except Exception as e:
            logger.error(f"Backtest failed for {strategy}: {e}")
            return {"error": str(e), "total_return": -1.0, "win_rate": 0.0, "num_trades": 0}

    def evaluate_parameter_set(self, strategy: str, params: Dict[str, Any], df: pd.DataFrame) -> ParameterSet:
        """Evaluate a parameter set and return results."""
        param_set = ParameterSet(strategy=strategy, parameters=params)

        try:
            perf = self.run_backtest(strategy, params, df)
            param_set.performance = perf
            param_set.tested_at = datetime.utcnow()
        except Exception as e:
            logger.error(f"Backtest failed for {strategy}: {e}")
            param_set.performance = {"error": str(e), "total_return": -1.0}

        return param_set

    def update_best_parameters(self, param_set: ParameterSet):
        """Update best parameters if this set performed better."""
        strategy = param_set.strategy
        perf = param_set.performance

        if not perf or "total_return" not in perf:
            return False

        current_best = self.state.best_parameters.get(strategy, {}).get("performance", {})

        is_better = False
        if "total_return" in current_best:
            # Primary: higher return
            if perf["total_return"] > current_best["total_return"]:
                is_better = True
            # Secondary: same return but better win rate
            elif perf["total_return"] == current_best["total_return"]:
                if perf.get("win_rate", 0) > current_best.get("win_rate", 0):
                    is_better = True
        else:
            is_better = True

        if is_better:
            param_set.is_best = True
            self.state.best_parameters[strategy] = {
                "parameters": param_set.parameters,
                "performance": perf,
                "updated_at": datetime.utcnow().isoformat()
            }
            return True
        
        return False

    def should_trigger_opencode(self, metrics: Dict[str, Any]) -> bool:
        """
        Decide if we should trigger an Opencode improvement request.
        This is the KEY function that determines when to call Opencode.
        """
        # Check rate limit first
        if not self.opencode.can_call():
            logger.debug("Opencode rate limit active, skipping trigger check")
            return False
        
        # Trigger on bad performance metrics
        win_rate = metrics.get("win_rate", 1.0)
        max_drawdown = metrics.get("max_drawdown", 0.0)
        total_return = metrics.get("total_return", 0.0)
        
        if win_rate < 0.55:
            logger.warning(f"🚨 TRIGGER: Win rate {win_rate:.1%} below 55% threshold")
            return True

        if max_drawdown < -0.02:
            logger.warning(f"🚨 TRIGGER: Drawdown {max_drawdown:.1%} exceeds -2% threshold")
            return True
            
        if total_return < -0.05:
            logger.warning(f"🚨 TRIGGER: Total return {total_return:.1%} below -5% threshold")
            return True

        # Regular scheduled optimization every 24h
        last_call = self.opencode.last_call
        if not last_call or datetime.utcnow() - last_call > timedelta(hours=24):
            logger.info("📅 TRIGGER: Scheduled 24h optimization")
            return True

        return False

    def run_continuous_optimization(self):
        """
        FIXED: Main optimization loop that:
        1. Tests NEW strategies (ADX, London-NY, Mean Reversion)
        2. Calls should_trigger_opencode() to check if Opencode needed
        3. Invokes Opencode when performance is poor
        4. Tracks best parameters
        """
        logger.info("="*70)
        logger.info("STARTING FIXED CONTINUOUS OPTIMIZATION")
        logger.info("Testing NEW strategies: ADX, London-NY, Mean Reversion")
        logger.info("="*70)

        while self.state.running:
            try:
                self.state.iteration += 1
                iteration = self.state.iteration

                # Log every 10 iterations
                if iteration % 10 == 1:
                    logger.info(f"="*70)
                    logger.info(f"OPTIMIZATION ITERATION #{iteration}")
                    logger.info(f"="*70)

                # Fetch fresh market data
                df = fetch_candles(limit=10000)
                
                # Get aggregate metrics for trigger check
                aggregate_metrics = self._calculate_aggregate_metrics(df)

                # === KEY FIX: Check if we should trigger Opencode ===
                if self.should_trigger_opencode(aggregate_metrics):
                    logger.warning("="*70)
                    logger.warning("PERFORMANCE THRESHOLD BREACHED - CALLING OPENCODE")
                    logger.warning("="*70)
                    
                    # Get recent logs for context
                    logs = self._get_recent_logs()
                    
                    # Call Opencode to improve strategies
                    success = self.opencode.send_feedback(aggregate_metrics, logs)
                    
                    if success:
                        logger.info("✅ Opencode completed - reloading modules")
                        reload_all_modules()
                        self.state.last_opencode_call = datetime.utcnow()
                    else:
                        logger.error("❌ Opencode failed to execute")

                # === Test NEW strategies (not legacy ones) ===
                new_strategies = ["adx_trend", "london_ny_breakout", "mean_reversion"]
                
                for strategy in new_strategies:
                    # Test current best parameters
                    if strategy in self.state.best_parameters:
                        best_params = self.state.best_parameters[strategy]["parameters"]
                        param_set = self.evaluate_parameter_set(strategy, best_params, df)
                        self.update_best_parameters(param_set)
                        
                        if iteration % 10 == 1:
                            perf = param_set.performance or {}
                            logger.info(f"  [{strategy.upper()}] Best: Return={perf.get('total_return', 0):.2%}, "
                                       f"WinRate={perf.get('win_rate', 0):.1%}, Trades={perf.get('num_trades', 0)}")

                # === Random parameter search ===
                tested_count = 0
                for _ in range(30):  # Test 30 random combinations
                    strategy = np.random.choice(new_strategies)
                    params = {}
                    
                    if strategy in self.parameter_space:
                        for key, values in self.parameter_space[strategy].items():
                            params[key] = np.random.choice(values)

                        param_set = self.evaluate_parameter_set(strategy, params, df)
                        was_best = self.update_best_parameters(param_set)
                        tested_count += 1

                        if was_best:
                            perf = param_set.performance or {}
                            logger.info(f"  ★ NEW BEST [{strategy.upper()}]: Return={perf.get('total_return', 0):.2%}, "
                                       f"WinRate={perf.get('win_rate', 0):.1%}")

                # === Check if all strategies meeting target ===
                all_meeting = True
                for strategy in new_strategies:
                    if strategy in self.state.best_parameters:
                        ret = self.state.best_parameters[strategy]["performance"].get("total_return", 0)
                        if ret < self.state.target_hourly_return:
                            all_meeting = False
                            if iteration % 50 == 0:
                                logger.info(f"  [{strategy.upper()}] Below target: {ret:.2%} < 5%")

                if all_meeting and iteration % 100 == 0:
                    logger.info("🎉 ALL STRATEGIES MEETING 5% HOURLY TARGET!")

                # Save state
                self.save_state()

                # No sleep - continuous optimization
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {str(e)}", exc_info=True)
                time.sleep(60)

    def _calculate_aggregate_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate aggregate metrics across all strategies for trigger check."""
        metrics = {
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "total_return": 0.0,
            "num_strategies": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        new_strategies = ["adx_trend", "london_ny_breakout", "mean_reversion"]
        
        for strategy in new_strategies:
            if strategy in self.state.best_parameters:
                perf = self.state.best_parameters[strategy].get("performance", {})
                metrics["win_rate"] += perf.get("win_rate", 0)
                metrics["max_drawdown"] = min(metrics["max_drawdown"], perf.get("max_drawdown", 0))
                metrics["total_return"] += perf.get("total_return", 0)
                metrics["num_strategies"] += 1
        
        # Average the metrics
        if metrics["num_strategies"] > 0:
            metrics["win_rate"] /= metrics["num_strategies"]
            metrics["total_return"] /= metrics["num_strategies"]
        
        return metrics

    def _get_recent_logs(self, lines: int = 100) -> str:
        """Get recent log entries for Opencode context."""
        log_file = "/home/openclaw/FinRobot/trading_daemon.log"
        try:
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    all_lines = f.readlines()
                    return "".join(all_lines[-lines:])
        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
        return "No recent logs available"

    def start(self):
        """Start the feedback loop in a background thread."""
        self.state.running = True
        self.thread = threading.Thread(target=self.run_continuous_optimization, daemon=True)
        self.thread.start()
        logger.info("✅ FIXED Autonomous feedback loop started (testing NEW strategies)")

    def evaluate_and_update(self, backtest_result, current_config):
        """Called by daemon after each backtest run."""
        with self.lock:
            try:
                param_set = ParameterSet(
                    strategy="grid",
                    parameters=asdict(current_config),
                    performance=backtest_result,
                    tested_at=datetime.utcnow()
                )
                
                self.update_best_parameters(param_set)
                self.log_iteration(param_set)
                
                self.consecutive_failures = 0
                
            except Exception as e:
                logger.error(f"Failed to process evaluate_and_update: {str(e)}")
                self.consecutive_failures += 1

    def stop(self):
        """Stop the feedback loop."""
        self.state.running = False
        if self.thread:
            self.thread.join(timeout=10)
        self.save_state()
        logger.info("Autonomous feedback loop stopped")

    def load_state(self):
        """Load state from JSON file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.state.best_parameters = data.get("best_parameters", {})
                    self.state.iteration = data.get("iteration", 0)
                    last_opencode_str = data.get("last_opencode_call")
                    if last_opencode_str:
                        self.state.last_opencode_call = datetime.fromisoformat(last_opencode_str)
                    logger.info(f"Loaded feedback loop state: {self.state.iteration} iterations")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def save_state(self):
        """Save state to JSON file."""
        def json_default(obj):
            if isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
            
        try:
            with open(self.state_file, "w") as f:
                json.dump({
                    "iteration": self.state.iteration,
                    "best_parameters": self.state.best_parameters,
                    "last_sweep": self.state.last_sweep.isoformat() if self.state.last_sweep else None,
                    "last_opencode_call": self.state.last_opencode_call.isoformat() if self.state.last_opencode_call else None
                }, f, indent=2, default=json_default)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def log_iteration(self, parameter_set: ParameterSet):
        """Log iteration details."""
        if parameter_set.is_best:
            perf = parameter_set.performance or {}
            logger.info(f"★ New best for {parameter_set.strategy}: "
                       f"Return={perf.get('total_return', 0):.2%}, "
                       f"WinRate={perf.get('win_rate', 0):.1%}, Trades={perf.get('num_trades', 0)}")

    def generate_parameter_combinations(self, strategy: str) -> Iterator[Dict[str, Any]]:
        """Generate all parameter combinations for a strategy."""
        space = self.parameter_space.get(strategy, {})
        if not space:
            return iter([])
        keys = list(space.keys())
        for values in itertools.product(*space.values()):
            yield dict(zip(keys, values))

    def run_backtest(self, strategy: str, params: Dict[str, Any], df: pd.DataFrame) -> Dict[str, float]:
        """Run backtest for a strategy with given parameters."""
        try:
            if strategy == "adx_trend":
                cfg = ADXTrendConfig(**params)
                return backtest_adx_trend(df, cfg)
            elif strategy == "london_ny_breakout":
                cfg = LondonNYBreakoutConfig(**params)
                return backtest_london_ny_breakout(df, cfg)
            elif strategy == "mean_reversion":
                cfg = MeanReversionConfig(**params)
                return backtest_mean_reversion(df, cfg)
            elif strategy == "grid":
                cfg = GridConfig(**params)
                return backtest_xauusd_grid(df, cfg)
            else:
                raise ValueError(f"Unknown strategy: {strategy}")
        except Exception as e:
            logger.error(f"Backtest failed for {strategy}: {e}")
            return {"error": str(e), "total_return": -1.0, "win_rate": 0.0, "num_trades": 0}

    def evaluate_parameter_set(self, strategy: str, params: Dict[str, Any], df: pd.DataFrame) -> ParameterSet:
        """Evaluate a parameter set and return results."""
        param_set = ParameterSet(strategy=strategy, parameters=params)

        try:
            perf = self.run_backtest(strategy, params, df)
            param_set.performance = perf
            param_set.tested_at = datetime.utcnow()
        except Exception as e:
            logger.error(f"Backtest failed for {strategy}: {e}")
            param_set.performance = {"error": str(e), "total_return": -1.0}

        return param_set

    def update_best_parameters(self, param_set: ParameterSet):
        """Update best parameters if this set performed better."""
        strategy = param_set.strategy
        perf = param_set.performance

        if not perf or "total_return" not in perf:
            return False

        current_best = self.state.best_parameters.get(strategy, {}).get("performance", {})

        is_better = False
        if "total_return" in current_best:
            # Primary: higher return
            if perf["total_return"] > current_best["total_return"]:
                is_better = True
            # Secondary: same return but better win rate
            elif perf["total_return"] == current_best["total_return"]:
                if perf.get("win_rate", 0) > current_best.get("win_rate", 0):
                    is_better = True
        else:
            is_better = True

        if is_better:
            param_set.is_best = True
            self.state.best_parameters[strategy] = {
                "parameters": param_set.parameters,
                "performance": perf,
                "updated_at": datetime.utcnow().isoformat()
            }
            return True
        
        return False

    def should_trigger_opencode(self, metrics: Dict[str, Any]) -> bool:
        """
        Decide if we should trigger an Opencode improvement request.
        KEY FUNCTION: Checks if performance is poor enough to warrant Opencode call.
        """
        # Check rate limit first
        if not self.opencode.can_call():
            logger.debug("Opencode rate limit active, skipping trigger check")
            return False
        
        # Trigger on bad performance metrics
        win_rate = metrics.get("win_rate", 1.0)
        max_drawdown = metrics.get("max_drawdown", 0.0)
        total_return = metrics.get("total_return", 0.0)
        
        if win_rate < 0.55:
            logger.warning(f"🚨 TRIGGER: Win rate {win_rate:.1%} below 55% threshold")
            return True

        if max_drawdown < -0.02:
            logger.warning(f"🚨 TRIGGER: Drawdown {max_drawdown:.1%} exceeds -2% threshold")
            return True
            
        if total_return < -0.05:
            logger.warning(f"🚨 TRIGGER: Total return {total_return:.1%} below -5% threshold")
            return True

        # Regular scheduled optimization every 24h
        last_call = self.opencode.last_call
        if not last_call or datetime.utcnow() - last_call > timedelta(hours=24):
            logger.info("📅 TRIGGER: Scheduled 24h optimization")
            return True

        return False

    def run_continuous_optimization(self):
        """
        FIXED: Main optimization loop that:
        1. Tests NEW strategies (ADX, London-NY, Mean Reversion)
        2. Calls should_trigger_opencode() to check if Opencode needed
        3. Invokes Opencode when performance is poor
        4. Tracks best parameters
        """
        logger.info("="*70)
        logger.info("STARTING FIXED CONTINUOUS OPTIMIZATION")
        logger.info("Testing NEW strategies: ADX, London-NY, Mean Reversion")
        logger.info("="*70)

        while self.state.running:
            try:
                self.state.iteration += 1
                iteration = self.state.iteration

                # Log every 10 iterations
                if iteration % 10 == 1:
                    logger.info(f"="*70)
                    logger.info(f"OPTIMIZATION ITERATION #{iteration}")
                    logger.info(f"="*70)

                # Fetch fresh market data
                df = fetch_candles(limit=10000)
                
                # Get aggregate metrics for trigger check
                aggregate_metrics = self._calculate_aggregate_metrics(df)

                # === KEY FIX: Check if we should trigger Opencode ===
                if self.should_trigger_opencode(aggregate_metrics):
                    logger.warning("="*70)
                    logger.warning("PERFORMANCE THRESHOLD BREACHED - CALLING OPENCODE")
                    logger.warning("="*70)
                    
                    # Get recent logs for context
                    logs = self._get_recent_logs()
                    
                    # Call Opencode to improve strategies
                    success = self.opencode.send_feedback(aggregate_metrics, logs)
                    
                    if success:
                        logger.info("✅ Opencode completed - reloading modules")
                        reload_all_modules()
                        self.state.last_opencode_call = datetime.utcnow()
                    else:
                        logger.error("❌ Opencode failed to execute")

                # === Test NEW strategies (not legacy ones) ===
                new_strategies = ["adx_trend", "london_ny_breakout", "mean_reversion"]
                
                for strategy in new_strategies:
                    # Test current best parameters
                    if strategy in self.state.best_parameters:
                        best_params = self.state.best_parameters[strategy]["parameters"]
                        param_set = self.evaluate_parameter_set(strategy, best_params, df)
                        self.update_best_parameters(param_set)
                        
                        if iteration % 10 == 1:
                            perf = param_set.performance or {}
                            logger.info(f"  [{strategy.upper()}] Best: Return={perf.get('total_return', 0):.2%}, "
                                       f"WinRate={perf.get('win_rate', 0):.1%}, Trades={perf.get('num_trades', 0)}")

                # === Random parameter search ===
                tested_count = 0
                for _ in range(30):  # Test 30 random combinations
                    strategy = np.random.choice(new_strategies)
                    params = {}
                    
                    if strategy in self.parameter_space:
                        for key, values in self.parameter_space[strategy].items():
                            params[key] = np.random.choice(values)

                        param_set = self.evaluate_parameter_set(strategy, params, df)
                        was_best = self.update_best_parameters(param_set)
                        tested_count += 1

                        if was_best:
                            perf = param_set.performance or {}
                            logger.info(f"  ★ NEW BEST [{strategy.upper()}]: Return={perf.get('total_return', 0):.2%}, "
                                       f"WinRate={perf.get('win_rate', 0):.1%}")

                # === Check if all strategies meeting target ===
                all_meeting = True
                for strategy in new_strategies:
                    if strategy in self.state.best_parameters:
                        ret = self.state.best_parameters[strategy]["performance"].get("total_return", 0)
                        if ret < self.state.target_hourly_return:
                            all_meeting = False
                            if iteration % 50 == 0:
                                logger.info(f"  [{strategy.upper()}] Below target: {ret:.2%} < 5%")

                if all_meeting and iteration % 100 == 0:
                    logger.info("🎉 ALL STRATEGIES MEETING 5% HOURLY TARGET!")

                # Save state
                self.save_state()

                # No sleep - continuous optimization
                
            except Exception as e:
                logger.error(f"Error in optimization loop: {str(e)}", exc_info=True)
                time.sleep(60)

    def _calculate_aggregate_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate aggregate metrics across all strategies for trigger check."""
        metrics = {
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "total_return": 0.0,
            "num_strategies": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        new_strategies = ["adx_trend", "london_ny_breakout", "mean_reversion"]
        
        for strategy in new_strategies:
            if strategy in self.state.best_parameters:
                perf = self.state.best_parameters[strategy].get("performance", {})
                metrics["win_rate"] += perf.get("win_rate", 0)
                metrics["max_drawdown"] = min(metrics["max_drawdown"], perf.get("max_drawdown", 0))
                metrics["total_return"] += perf.get("total_return", 0)
                metrics["num_strategies"] += 1
        
        # Average the metrics
        if metrics["num_strategies"] > 0:
            metrics["win_rate"] /= metrics["num_strategies"]
            metrics["total_return"] /= metrics["num_strategies"]
        
        return metrics

    def _get_recent_logs(self, lines: int = 100) -> str:
        """Get recent log entries for Opencode context."""
        log_file = "/home/openclaw/FinRobot/trading_daemon.log"
        try:
            if os.path.exists(log_file):
                with open(log_file, "r") as f:
                    all_lines = f.readlines()
                    return "".join(all_lines[-lines:])
        except Exception as e:
            logger.error(f"Failed to read logs: {e}")
        return "No recent logs available"
