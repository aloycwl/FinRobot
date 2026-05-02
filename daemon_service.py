from __future__ import annotations

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

from finrobot.config import settings
from finrobot.data_sources import fetch_candles
from finrobot.grid import GridConfig, backtest_xauusd_grid, calculate_trend_direction
from finrobot.backtesting import BacktestConfig, backtest_trend_martingale
from finrobot.hft import HFTConfig, backtest_hft
from finrobot.feedback_loop import AutonomousFeedbackLoop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("/home/openclaw/FinRobot/trading_daemon.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("trading_daemon")


@dataclass
class DaemonState:
    running: bool = False
    last_check: Optional[datetime] = None
    trend: int = 0
    active_positions: int = 0
    total_trades: int = 0
    pnl: float = 0.0
    current_price: float = 0.0


class TradingDaemon:
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.state = DaemonState()
        self.grid_config = GridConfig()
        self.state_file = "/home/openclaw/FinRobot/daemon_state.json"
        self.pid_file = "/home/openclaw/FinRobot/daemon.pid"
        self.feedback_loop = AutonomousFeedbackLoop(self)

    def start(self):
        if os.path.exists(self.pid_file):
            with open(self.pid_file, "r") as f:
                old_pid = f.read().strip()
            if os.path.exists(f"/proc/{old_pid}"):
                logger.error(f"Daemon already running with PID {old_pid}")
                sys.exit(1)
            else:
                os.unlink(self.pid_file)

        with open(self.pid_file, "w") as f:
            f.write(str(os.getpid()))

        logger.info("Trading daemon started")
        self.state.running = True
        self.feedback_loop.start()
        self.run_loop()

    def stop(self):
        self.state.running = False
        self.feedback_loop.stop()
        if os.path.exists(self.pid_file):
            os.unlink(self.pid_file)
        logger.info("Trading daemon stopped")

    def save_state(self):
        with open(self.state_file, "w") as f:
            json.dump({
                **self.state.__dict__,
                "last_check": self.state.last_check.isoformat() if self.state.last_check else None
            }, f, indent=2)

    def run_loop(self):
        try:
            while self.state.running:
                self.run_cycle()
                self.save_state()
                # Sleep to prevent CPU exhaustion
                time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()

    def run_cycle(self):
        """Run backtesting cycle for all three strategies."""
        try:
            # Fetch data from local CSV (10000 bars)
            df = fetch_candles(limit=10000)
            self.state.last_check = datetime.utcnow()

            if len(df) == 0:
                logger.warning("No market data available, skipping cycle")
                return

            self.state.current_price = float(df.iloc[-1]["close"])

            # Get current iteration from feedback loop state
            iteration = 381  # Default, will be updated from state file
            try:
                with open("/home/openclaw/FinRobot/feedback_loop_state.json", 'r') as f:
                    state_data = json.load(f)
                    iteration = state_data.get('iteration', 381)
            except:
                pass

            # Run all three strategies and collect results
            results = {}
            errors = []

            # Strategy 1: Grid Trading (XAUUSD optimized)
            try:
                grid_result = backtest_xauusd_grid(df, self.grid_config)
                results['grid'] = grid_result
                if 'error' not in grid_result:
                    self.feedback_loop.evaluate_and_update(grid_result, self.grid_config)
            except Exception as e:
                errors.append(f"G:{str(e)[:15]}")

            # Strategy 2: Martingale Trend Following
            try:
                martingale_config = BacktestConfig()
                martingale_result = backtest_trend_martingale(df, martingale_config)
                results['mart'] = martingale_result
            except Exception as e:
                errors.append(f"M:{str(e)[:15]}")

            # Strategy 3: HFT (High Frequency)
            try:
                hft_config = HFTConfig()
                hft_result = backtest_hft(df, hft_config)
                results['hft'] = hft_result
            except Exception as e:
                errors.append(f"H:{str(e)[:15]}")

            # Build concise progress line
            price = self.state.current_price
            gr = results.get('grid', {})
            mr = results.get('mart', {})
            hr = results.get('hft', {})

            # Format returns
            gr_ret = gr.get('total_return', 0) if 'error' not in gr else -999
            mr_ret = mr.get('total_return', 0) if 'error' not in mr else -999
            hr_ret = hr.get('total_return', 0) if 'error' not in hr else -999

            # Format win rates
            gr_wr = gr.get('win_rate', 0) if 'error' not in gr else 0
            mr_wr = mr.get('win_rate', 0) if 'error' not in mr else 0
            hr_wr = hr.get('win_rate', 0) if 'error' not in hr else 0

            # Count trades
            gr_tr = gr.get('total_trades', 0) if 'error' not in gr else 0
            mr_tr = mr.get('num_trades', 0) if 'error' not in mr else 0
            hr_tr = hr.get('num_trades', 0) if 'error' not in hr else 0

            # Progress percentage (target: 10000 iterations)
            progress_pct = min(100, (iteration / 10000) * 100)

            # Best strategy indicator
            best_strat = "-"
            best_ret = max(gr_ret, mr_ret, hr_ret)
            if best_ret > -999:
                if best_ret == gr_ret:
                    best_strat = "G"
                elif best_ret == mr_ret:
                    best_strat = "M"
                else:
                    best_strat = "H"

            # Error indicator
            err_str = f"[E:{len(errors)}]" if errors else ""

            # Output format:
            # [ITER: 381/10000 3.8%] Price: 4566.70 | G:-0.45%|19.9%|5 M:-0.99%|19.9%|7629 H:0.00%|0.0%|0 | Best:M [E:0]
            log_line = (
                f"[ITER: {iteration}/10000 {progress_pct:.1f}%] "
                f"Price: {price:.2f} | "
                f"G:{gr_ret:+.2f}%|{gr_wr*100:.1f}%|{gr_tr} "
                f"M:{mr_ret:+.2f}%|{mr_wr*100:.1f}%|{mr_tr} "
                f"H:{hr_ret:+.2f}%|{hr_wr*100:.1f}%|{hr_tr} | "
                f"Best:{best_strat} {err_str}"
            )

            logger.info(log_line)

            # Only log detailed summaries every 100 cycles or on errors
            if iteration % 100 == 0 or errors:
                summary = (
                    f"=== SUMMARY Cycle #{iteration} ===\n"
                    f"  GRID:  Ret={gr_ret:+.2f}% Win={gr_wr*100:.1f}% Trades={gr_tr}\n"
                    f"  MART:  Ret={mr_ret:+.2f}% Win={mr_wr*100:.1f}% Trades={mr_tr}\n"
                    f"  HFT:   Ret={hr_ret:+.2f}% Win={hr_wr*100:.1f}% Trades={hr_tr}\n"
                    f"  Progress: {progress_pct:.1f}% | Best: {best_strat}"
                )
                logger.info(summary)

        except Exception as e:
            logger.error(f"Error in cycle: {str(e)}")


def print_status():
    state_file = "/home/openclaw/FinRobot/daemon_state.json"
    pid_file = "/home/openclaw/FinRobot/daemon.pid"

    print("\n=== Trading Daemon Status ===")
    if os.path.exists(pid_file):
        with open(pid_file) as f:
            print(f"✅ Running (PID: {f.read().strip()})")
    else:
        print("❌ Not running")

    if os.path.exists(state_file):
        with open(state_file) as f:
            state = json.load(f)
            print(f"\nLast check: {state.get('last_check', 'Never')}")
            print(f"Current price: {state.get('current_price', 0):.2f}")
            trend = "BULLISH" if state.get('trend') == 1 else "BEARISH" if state.get('trend') == -1 else "NEUTRAL"
            print(f"Trend direction: {trend}")
            print(f"Total trades: {state.get('total_trades', 0)}")
            print(f"PnL: {state.get('pnl', 0):.4f}")

    print("\nLog files:")
    print("  Trading daemon: /home/openclaw/FinRobot/trading_daemon.log")
    print("  Feedback loop:  /home/openclaw/FinRobot/feedback_iterations.log")

    # Show best parameters
    state_file = "/home/openclaw/FinRobot/feedback_loop_state.json"
    if os.path.exists(state_file):
        print("\n=== Best Performing Parameters ===")
        with open(state_file) as f:
            state = json.load(f)
            best = state.get("best_parameters", {})
            for strategy, data in best.items():
                perf = data.get("performance", {})
                print(f"\n{strategy.upper()}:")
                print(f"  Total return: {perf.get('total_return', 0):.2%}")
                print(f"  Win rate: {perf.get('win_rate', 0):.1%}")
                print(f"  Max drawdown: {perf.get('max_drawdown', 0):.2%}")

    print("\nCommands:")
    print("  python daemon_service.py start   # Start daemon with feedback loop")
    print("  python daemon_service.py stop    # Stop daemon")
    print("  python daemon_service.py status  # Show status")
    print("  python daemon_service.py sweep   # Run full parameter sweep")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_status()
        sys.exit(0)

    command = sys.argv[1].lower()

    daemon = TradingDaemon()

    if command == "start":
        daemon.start()
    elif command == "stop":
        daemon.stop()
    elif command == "status":
        print_status()
    elif command == "sweep":
        print("Starting full parameter sweep...")
        daemon.feedback_loop.run_parameter_sweep()
        print("Parameter sweep completed")
    else:
        print(f"Unknown command: {command}")
        print_status()
