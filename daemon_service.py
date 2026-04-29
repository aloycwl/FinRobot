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
from finrobot.data_sources import fetch_okx_candles
from finrobot.grid import GridConfig, backtest_xauusd_grid, calculate_trend_direction
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
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()

    def run_cycle(self):
        self.state.last_check = datetime.utcnow()
        logger.info("Running market check cycle")

        try:
            # Fetch latest 1min candles
            df = fetch_okx_candles(limit=500)
            self.state.current_price = float(df.iloc[-1]["close"])

            # Calculate trend direction
            df_with_trend = calculate_trend_direction(df, self.grid_config)
            self.state.trend = int(df_with_trend.iloc[-1]["trend"])

            trend_str = "BULLISH" if self.state.trend == 1 else "BEARISH" if self.state.trend == -1 else "NEUTRAL"
            logger.info(f"Current price: {self.state.current_price:.2f} | Trend: {trend_str}")

            # Run rolling backtest validation
            bt_result = backtest_xauusd_grid(df.tail(1000), self.grid_config)
            logger.info(f"Last 1000 bars stats: Win rate {bt_result['win_rate']:.1%}, Total return {bt_result['total_return']:.2%}")

        except Exception as e:
            logger.error(f"Error in cycle: {str(e)}", exc_info=True)


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
