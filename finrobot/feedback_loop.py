from __future__ import annotations

import os
import json
import time
import logging
import itertools
import threading
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Iterator
import pandas as pd
import numpy as np

from finrobot.config import settings
from finrobot.data_sources import fetch_okx_candles, fetch_candles
from finrobot.backtesting import backtest_trend_martingale, BacktestConfig
from finrobot.grid import GridConfig, backtest_xauusd_grid
from finrobot.hft import HFTConfig, backtest_hft
from finrobot.opencode_integration import OpencodeFeedbackLoop
from finrobot.hot_reload import reload_all_modules


logger = logging.getLogger("feedback_loop")


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


class AutonomousFeedbackLoop:
    def __init__(self, daemon):
        self.daemon = daemon
        self.state = FeedbackLoopState()
        self.state_file = "./feedback_loop_state.json"
        self.log_file = "./feedback_iterations.log"
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.opencode = OpencodeFeedbackLoop()
        self.consecutive_failures = 0

        self.parameter_space = {
            "grid": {
                "grid_step_pips": [0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0],
                "take_profit_pips": [0.3, 0.5, 1.0, 1.5, 2.0, 3.0],
                "trend_ema_fast": [3, 5, 8, 12, 21],
                "trend_ema_slow": [8, 15, 21, 34, 55],
                "max_grid_levels": [2, 4, 6, 8, 12],
                "base_lot": [0.005, 0.01, 0.02, 0.05]
            },
            "martingale": {
                "multiplier": [1.25, 1.5, 1.75, 2.0, 2.25, 2.5],
                "base_lot": [0.005, 0.01, 0.02, 0.03],
                "max_steps": [2, 3, 4, 5, 6],
                "ema_fast": [3, 5, 8],
                "ema_slow": [12, 20, 34]
            },
            "hft": {
                "tick_threshold": [0.02, 0.05, 0.08, 0.12],
                "volume_filter": [10, 25, 50, 100],
                "latency_ms": [50, 100, 200],
                "spread_limit": [0.01, 0.02, 0.03]
            }
        }

        self.load_state()

    def load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.state.best_parameters = data.get("best_parameters", {})
                    self.state.iteration = data.get("iteration", 0)
                    logger.info(f"Loaded feedback loop state: {self.state.iteration} iterations")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def save_state(self):
        def json_default(obj):
            if isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
            
        with open(self.state_file, "w") as f:
            json.dump({
                "iteration": self.state.iteration,
                "best_parameters": self.state.best_parameters,
                "last_sweep": self.state.last_sweep.isoformat() if self.state.last_sweep else None
            }, f, indent=2, default=json_default)

    def log_iteration(self, parameter_set: ParameterSet):
        def json_default(obj):
            if isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            if isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
            
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "strategy": parameter_set.strategy,
            "parameters": parameter_set.parameters,
            "performance": parameter_set.performance,
            "is_best": parameter_set.is_best
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(log_entry, default=json_default) + "\n")

    def generate_parameter_combinations(self, strategy: str) -> Iterator[Dict[str, Any]]:
        space = self.parameter_space[strategy]
        keys = list(space.keys())
        for values in itertools.product(*space.values()):
            yield dict(zip(keys, values))

    def run_backtest(self, strategy: str, params: Dict[str, Any], df: pd.DataFrame) -> Dict[str, float]:
        if strategy == "grid":
            cfg = GridConfig(**params)
            return backtest_xauusd_grid(df, cfg)
        elif strategy == "martingale":
            cfg = BacktestConfig(**params)
            return backtest_trend_martingale(df, cfg)
        elif strategy == "hft":
            cfg = HFTConfig(**params)
            return backtest_hft(df, cfg)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def evaluate_parameter_set(self, strategy: str, params: Dict[str, Any], df: pd.DataFrame) -> ParameterSet:
        param_set = ParameterSet(strategy=strategy, parameters=params)

        try:
            perf = self.run_backtest(strategy, params, df)
            param_set.performance = perf
            param_set.tested_at = datetime.utcnow()
        except Exception as e:
            logger.error(f"Backtest failed for {strategy}: {e}")
            param_set.performance = {"error": str(e)}

        return param_set

    def update_best_parameters(self, param_set: ParameterSet):
        strategy = param_set.strategy
        perf = param_set.performance

        if not perf or "total_return" not in perf:
            return

        current_best = self.state.best_parameters.get(strategy, {}).get("performance", {})

        if "total_return" in current_best:
            if perf["total_return"] > current_best["total_return"]:
                param_set.is_best = True
                self.state.best_parameters[strategy] = {
                    "parameters": param_set.parameters,
                    "performance": perf,
                    "updated_at": datetime.utcnow().isoformat()
                }
                logger.info(f"New best parameters for {strategy}: {perf['total_return']:.2%}")
        else:
            param_set.is_best = True
            self.state.best_parameters[strategy] = {
                "parameters": param_set.parameters,
                "performance": perf,
                "updated_at": datetime.utcnow().isoformat()
            }

    def run_parameter_sweep(self):
        logger.info("Starting full parameter sweep across all strategies")
        df = fetch_candles(limit=10000)

        for strategy in ["grid", "martingale", "hft"]:
            logger.info(f"Running parameter sweep for {strategy}")
            tested = 0
            best_return = -np.inf

            for params in self.generate_parameter_combinations(strategy):
                param_set = self.evaluate_parameter_set(strategy, params, df)
                self.state.tested_parameters.append(param_set)
                self.update_best_parameters(param_set)
                self.log_iteration(param_set)

                tested += 1
                if tested % 20 == 0:
                    logger.info(f"Tested {tested} {strategy} parameter sets")

                time.sleep(0.05)

            logger.info(f"Completed {strategy} sweep: {tested} sets tested")

        self.state.last_sweep = datetime.utcnow()
        self.save_state()

    def run_continuous_optimization(self):
        logger.info("Starting continuous optimization loop")

        while self.state.running:
            try:
                self.state.iteration += 1
                logger.info(f"Starting optimization iteration #{self.state.iteration}")

                # Fetch fresh market data - 10000 bars minimum for accuracy
                df = fetch_candles(limit=10000)

                # Test current best parameters first
                for strategy in ["grid", "martingale", "hft"]:
                    if strategy in self.state.best_parameters and "parameters" in self.state.best_parameters[strategy]:
                        best_params = self.state.best_parameters[strategy]["parameters"]
                        param_set = self.evaluate_parameter_set(strategy, best_params, df)
                        self.log_iteration(param_set)
                        logger.info(f"{strategy} baseline performance: {param_set.performance.get('total_return', 0):.2%}")

                # Run limited parameter search (50 random combinations)
                for _ in range(50):
                    strategy = np.random.choice(["grid", "martingale", "hft"])
                    params = {}
                    for key, values in self.parameter_space[strategy].items():
                        params[key] = np.random.choice(values)

                    param_set = self.evaluate_parameter_set(strategy, params, df)
                    self.state.tested_parameters.append(param_set)
                    self.update_best_parameters(param_set)
                    self.log_iteration(param_set)

                # Check for 5% hourly target
                all_met_target = True
                working_strategies = 0
                for strategy in ["grid", "martingale", "hft"]:
                    if strategy in self.state.best_parameters and "parameters" in self.state.best_parameters[strategy]:
                        working_strategies += 1
                        ret = self.state.best_parameters[strategy]["performance"].get("total_return", 0)
                        if ret < self.state.target_hourly_return:
                            all_met_target = False
                            logger.info(f"{strategy} not meeting target: {ret:.2%} < 5%")

                # Trigger opencode also if no working strategies after 10 iterations
                if working_strategies == 0 and self.state.iteration >= 10 and self.opencode.can_call():
                    logger.warning("No working strategies found after multiple iterations. Requesting code fix from opencode.")
                    with open(self.log_file, "r") as f:
                        last_logs = f.readlines()[-100:]
                    self.opencode.send_feedback({"no_working_strategies": True, "iterations": self.state.iteration}, "\n".join(last_logs))
                    reload_all_modules()

                if all_met_target:
                    logger.info("✅ All strategies meeting 5% hourly return target")

                self.save_state()
                
                # Only update daemon if we actually have working best parameters
                if "grid" in self.state.best_parameters and "parameters" in self.state.best_parameters["grid"]:
                    self.daemon.grid_config = GridConfig(**self.state.best_parameters["grid"]["parameters"])
                    logger.info("Updated daemon with latest best parameters")

                # Check failure rate
                failure_rate = sum(1 for p in self.state.tested_parameters[-50:] if "error" in p.performance) / max(1, len(self.state.tested_parameters[-50:]))
                
                # Call opencode when 80%+ failures detected
                if failure_rate > 0.8 and self.opencode.can_call():
                    logger.warning(f"High failure rate detected: {failure_rate:.0%}. Calling opencode for automatic improvements.")
                    
                    # Get last 50 logs
                    with open(self.log_file, "r") as f:
                        last_logs = f.readlines()[-50:]
                    
                    metrics = {
                        "failure_rate": failure_rate,
                        "consecutive_failures": self.consecutive_failures,
                        "total_iterations": self.state.iteration,
                        "working_strategies": list(self.state.best_parameters.keys())
                    }
                    
                    # Execute automatic code improvement
                    success = self.opencode.send_feedback(metrics, "\n".join(last_logs))
                    
                    if success:
                        logger.info("✅ Opencode completed successfully, hot reloading all modules")
                        reload_all_modules()
                        self.consecutive_failures = 0
                    else:
                        logger.error("❌ Opencode failed to run")
                        self.consecutive_failures += 1

                # No sleep - continuous optimization loop
                pass

            except Exception as e:
                logger.error(f"Error in optimization loop: {str(e)}", exc_info=True)
                time.sleep(60)

    def start(self):
        self.state.running = True
        self.thread = threading.Thread(target=self.run_continuous_optimization, daemon=True)
        self.thread.start()
        logger.info("Autonomous feedback loop started")

    def evaluate_and_update(self, backtest_result, current_config):
        """
        Called by daemon after each backtest run in main loop.
        Updates best parameters and tracks performance from daemon cycle results.
        """
        with self.lock:
            try:
                param_set = ParameterSet(
                    strategy="grid",
                    parameters=asdict(current_config),
                    performance=backtest_result,
                    tested_at=datetime.utcnow()
                )
                
                self.state.tested_parameters.append(param_set)
                self.update_best_parameters(param_set)
                self.log_iteration(param_set)
                
                self.consecutive_failures = 0
                logger.debug(f"Received daemon backtest result: {backtest_result.get('total_return', 0):.2%}")
                
            except Exception as e:
                logger.error(f"Failed to process evaluate_and_update: {str(e)}")
                self.consecutive_failures += 1

    def stop(self):
        self.state.running = False
        if self.thread:
            self.thread.join(timeout=10)
        self.save_state()
        logger.info("Autonomous feedback loop stopped")
