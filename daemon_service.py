#!/usr/bin/env python3
"""
Trading Daemon Service - IMPROVED VERSION

Key improvements:
- Garbage collection after each cycle
- Memory management (explicit DataFrame cleanup)
- Longer sleep intervals (30s instead of 5s)
- Better error recovery with restart logic
- PID file cleanup on startup
- Health monitoring with memory tracking
"""

from __future__ import annotations

import os
import sys
import gc
import time
import json
import logging
import signal
import traceback
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

# Optional psutil for memory monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("Warning: psutil not available, memory monitoring disabled")

from finrobot.config import settings
from finrobot.data_sources import fetch_candles
from finrobot.grid import GridConfig, backtest_xauusd_grid
from finrobot.backtesting import BacktestConfig, backtest_trend_martingale
from finrobot.hft import HFTConfig, backtest_hft
from finrobot.feedback_loop import AutonomousFeedbackLoop

# ============================================================================
# Configuration
# ============================================================================

SLEEP_INTERVAL = 30  # Increased from 5 to 30 seconds between cycles
MEMORY_THRESHOLD_MB = 500  # Restart if memory exceeds this
GC_INTERVAL = 10  # Force garbage collection every N cycles
MAX_ERRORS_BEFORE_RESTART = 5  # Restart after this many consecutive errors

# ============================================================================
# Logging Setup with Rotation
# ============================================================================

from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

# Rotating file handler (10MB max, keep 5 backups)
file_handler = RotatingFileHandler(
    "/home/openclaw/FinRobot/trading_daemon.log",
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
file_handler.setFormatter(log_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger("trading_daemon")

# ============================================================================
# Health Monitor
# ============================================================================

class HealthMonitor:
    def __init__(self):
        self.error_count = 0
        self.cycle_count = 0
        self.last_memory_mb = 0
        # Only initialize psutil process if available
        if PSUTIL_AVAILABLE:
            try:
                self.process = psutil.Process()
            except:
                self.process = None
        else:
            self.process = None
        
    def check_health(self) -> Dict[str, Any]:
        """Check system health and return status."""
        # Try to get memory info if psutil is available
        memory_mb = 0
        if PSUTIL_AVAILABLE and self.process:
            try:
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024
                self.last_memory_mb = memory_mb
            except:
                pass
        
        health = {
            "status": "healthy",
            "memory_mb": round(memory_mb, 2),
            "memory_threshold_mb": MEMORY_THRESHOLD_MB,
            "error_count": self.error_count,
            "cycle_count": self.cycle_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check for memory threshold (only if we can measure it)
        if memory_mb > 0 and memory_mb > MEMORY_THRESHOLD_MB:
            health["status"] = "critical_memory"
            logger.warning(f"Memory usage {memory_mb:.1f}MB exceeds threshold {MEMORY_THRESHOLD_MB}MB")
            
        # Check for too many errors
        if self.error_count >= MAX_ERRORS_BEFORE_RESTART:
            health["status"] = "too_many_errors"
            logger.error(f"Error count {self.error_count} exceeds threshold {MAX_ERRORS_BEFORE_RESTART}")
            
        return health
    
    def record_error(self):
        """Record an error occurrence."""
        self.error_count += 1
        
    def record_success(self):
        """Record a successful cycle."""
        self.error_count = max(0, self.error_count - 1)  # Decay error count
        self.cycle_count += 1
        
    def should_force_gc(self) -> bool:
        """Check if we should force garbage collection."""
        return self.cycle_count % GC_INTERVAL == 0

# ============================================================================
# Daemon State
# ============================================================================

@dataclass
class DaemonState:
    running: bool = False
    last_check: Optional[datetime] = None
    trend: int = 0
    active_positions: int = 0
    total_trades: int = 0
    pnl: float = 0.0
    current_price: float = 0.0

# ============================================================================
# Main Trading Daemon
# ============================================================================

class TradingDaemon:
    def __init__(self, check_interval: int = SLEEP_INTERVAL):
        self.check_interval = check_interval
        self.state = DaemonState()
        self.grid_config = GridConfig()
        self.state_file = "/home/openclaw/FinRobot/daemon_state.json"
        self.pid_file = "/home/openclaw/FinRobot/daemon.pid"
        self.health = HealthMonitor()
        self.feedback_loop = None
        self._shutdown_requested = False
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self._shutdown_requested = True
        self.stop()

    def _cleanup_pid_file(self):
        """Clean up stale PID file if process is dead."""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, "r") as f:
                    old_pid = f.read().strip()
                
                # Check if process exists
                if old_pid and os.path.exists(f"/proc/{old_pid}"):
                    try:
                        os.kill(int(old_pid), 0)  # Signal 0 checks if process exists
                        logger.error(f"Daemon already running with PID {old_pid}")
                        return False
                    except (OSError, ProcessLookupError):
                        # Process doesn't exist, clean up
                        pass
                
                # Clean up stale PID file
                logger.info(f"Cleaning up stale PID file for PID {old_pid}")
                os.unlink(self.pid_file)
                
            except Exception as e:
                logger.warning(f"Error checking PID file: {e}")
                # Try to remove anyway
                try:
                    os.unlink(self.pid_file)
                except:
                    pass
        
        return True

    def start(self):
        """Start the daemon with proper initialization."""
        # Clean up stale PID file
        if not self._cleanup_pid_file():
            sys.exit(1)

        # Write PID file
        try:
            with open(self.pid_file, "w") as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.error(f"Failed to write PID file: {e}")
            sys.exit(1)

        logger.info("=" * 60)
        logger.info("Trading Daemon Starting (IMPROVED VERSION)")
        logger.info("=" * 60)
        logger.info(f"PID: {os.getpid()}")
        logger.info(f"Sleep interval: {self.check_interval}s")
        logger.info(f"Memory threshold: {MEMORY_THRESHOLD_MB}MB")
        logger.info(f"GC interval: every {GC_INTERVAL} cycles")
        logger.info("=" * 60)

        # Initialize feedback loop
        try:
            self.feedback_loop = AutonomousFeedbackLoop(self)
            self.feedback_loop.start()
            logger.info("Feedback loop initialized")
        except Exception as e:
            logger.warning(f"Could not initialize feedback loop: {e}")
            self.feedback_loop = None

        self.state.running = True
        self.run_loop()

    def stop(self):
        """Stop the daemon gracefully."""
        logger.info("Stopping daemon...")
        self.state.running = False
        
        if self.feedback_loop:
            try:
                self.feedback_loop.stop()
            except Exception as e:
                logger.warning(f"Error stopping feedback loop: {e}")

        # Clean up PID file
        if os.path.exists(self.pid_file):
            try:
                os.unlink(self.pid_file)
                logger.info("PID file removed")
            except Exception as e:
                logger.warning(f"Error removing PID file: {e}")

        logger.info("Daemon stopped")

    def save_state(self):
        """Save daemon state to file."""
        try:
            with open(self.state_file, "w") as f:
                json.dump({
                    **self.state.__dict__,
                    "last_check": self.state.last_check.isoformat() if self.state.last_check else None
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")

    def run_loop(self):
        """Main daemon loop with health monitoring and error recovery."""
        consecutive_errors = 0
        
        while self.state.running and not self._shutdown_requested:
            try:
                # Check health before running cycle
                health = self.health.check_health()
                
                if health["status"] == "critical_memory":
                    logger.error("CRITICAL: Memory threshold exceeded, forcing restart")
                    self._force_restart()
                    return
                    
                if health["status"] == "too_many_errors":
                    logger.error("CRITICAL: Too many consecutive errors, restarting")
                    self._force_restart()
                    return

                # Run the main cycle
                self.run_cycle()
                
                # Record success and save state
                self.health.record_success()
                self.save_state()
                
                # Force garbage collection periodically
                if self.health.should_force_gc():
                    self._force_garbage_collection()
                
                consecutive_errors = 0  # Reset error count on success
                
            except Exception as e:
                consecutive_errors += 1
                self.health.record_error()
                logger.error(f"Error in main loop (consecutive: {consecutive_errors}): {e}")
                logger.error(traceback.format_exc())
                
                # Save error state
                try:
                    with open("/home/openclaw/FinRobot/daemon_errors.log", "a") as f:
                        f.write(f"{datetime.utcnow().isoformat()}: {e}\n")
                        f.write(traceback.format_exc())
                        f.write("\n" + "="*60 + "\n")
                except:
                    pass
            
            # Sleep before next iteration
            if self.state.running and not self._shutdown_requested:
                time.sleep(self.check_interval)

    def _force_garbage_collection(self):
        """Force garbage collection and log memory stats."""
        try:
            import gc
            gc.collect()  # Collect garbage
            
            # Log memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            logger.info(f"GC completed. Memory usage: {memory_mb:.1f}MB")
            
        except Exception as e:
            logger.warning(f"Error during garbage collection: {e}")

    def _force_restart(self):
        """Force daemon restart."""
        logger.info("Initiating daemon restart...")
        self.stop()
        
        # Small delay to ensure cleanup
        time.sleep(2)
        
        # Restart process
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            logger.error(f"Failed to restart: {e}")
            sys.exit(1)

    def run_cycle(self):
        """Run backtesting cycle for all three strategies with memory management."""
        df = None  # Will hold the data
        
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
                if 'error' not in grid_result and self.feedback_loop:
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

            # Output format
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

        finally:
            # ALWAYS clean up DataFrame to free memory
            if df is not None:
                del df
                df = None

    def _force_garbage_collection(self):
        """Force garbage collection and log memory stats."""
        try:
            gc.collect()  # Collect garbage
            
            # Log memory usage
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            logger.info(f"GC completed. Memory usage: {memory_mb:.1f}MB")
            
        except Exception as e:
            logger.warning(f"Error during garbage collection: {e}")

    def _force_restart(self):
        """Force daemon restart."""
        logger.info("Initiating daemon restart...")
        self.stop()
        
        # Small delay to ensure cleanup
        time.sleep(2)
        
        # Restart process
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            logger.error(f"Failed to restart: {e}")
            sys.exit(1)


# ============================================================================
# Status Functions
# ============================================================================

def print_status():
    state_file = "/home/openclaw/FinRobot/daemon_state.json"
    pid_file = "/home/openclaw/FinRobot/daemon.pid"

    print("\n" + "=" * 60)
    print("Trading Daemon Status (IMPROVED VERSION)")
    print("=" * 60)
    
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                pid = f.read().strip()
            # Check if process is actually running
            if pid and os.path.exists(f"/proc/{pid}"):
                print(f"✅ Running (PID: {pid})")
                
                # Get process info
                try:
                    proc = psutil.Process(int(pid))
                    mem_mb = proc.memory_info().rss / 1024 / 1024
                    cpu_pct = proc.cpu_percent(interval=0.1)
                    print(f"   Memory: {mem_mb:.1f}MB | CPU: {cpu_pct:.1f}%")
                except:
                    pass
            else:
                print(f"⚠️  Stale PID file (PID: {pid} not running)")
        except Exception as e:
            print(f"❌ Error reading PID file: {e}")
    else:
        print("❌ Not running (no PID file)")

    if os.path.exists(state_file):
        try:
            with open(state_file) as f:
                state = json.load(f)
                print(f"\n📊 Last State:")
                print(f"   Last check: {state.get('last_check', 'Never')}")
                print(f"   Current price: {state.get('current_price', 0):.2f}")
                trend = "BULLISH" if state.get('trend') == 1 else "BEARISH" if state.get('trend') == -1 else "NEUTRAL"
                print(f"   Trend: {trend}")
                print(f"   Total trades: {state.get('total_trades', 0)}")
                print(f"   PnL: {state.get('pnl', 0):.4f}")
        except Exception as e:
            print(f"\n⚠️  Error reading state file: {e}")

    # Show best parameters
    feedback_state_file = "/home/openclaw/FinRobot/feedback_loop_state.json"
    if os.path.exists(feedback_state_file):
        try:
            with open(feedback_state_file) as f:
                state = json.load(f)
                best = state.get("best_parameters", {})
                iteration = state.get("iteration", 0)
                print(f"\n🎯 Optimization Progress (Iteration #{iteration}):")
                for strategy, data in best.items():
                    perf = data.get("performance", {})
                    ret = perf.get('total_return', 0)
                    wr = perf.get('win_rate', 0)
                    dd = perf.get('max_drawdown', 0)
                    print(f"   {strategy.upper()}: Ret={ret:+.2%} WR={wr:.1%} DD={dd:.2%}")
        except Exception as e:
            print(f"\n⚠️  Error reading feedback state: {e}")

    print("\n" + "=" * 60)
    print("Commands:")
    print("  python daemon_service.py start   # Start daemon")
    print("  python daemon_service.py stop    # Stop daemon")
    print("  python daemon_service.py status  # Show status")
    print("  python daemon_service.py restart # Restart daemon")
    print("=" * 60 + "\n")


# ============================================================================
# Main Entry Point
# ============================================================================

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
    elif command == "restart":
        daemon.stop()
        time.sleep(2)
        daemon.start()
    elif command == "sweep":
        print("Starting full parameter sweep...")
        daemon.feedback_loop.run_parameter_sweep()
        print("Parameter sweep completed")
    else:
        print(f"Unknown command: {command}")
        print_status()
