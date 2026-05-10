#!/usr/bin/env python3
"""
Health Check and Watchdog for Moonshot Daemon
Monitors the daemon process, checks logs for staleness, and restarts if needed
"""

import os
import sys
import time
import json
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path

os.makedirs("/home/openclaw/FinRobot/logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('/home/openclaw/FinRobot/logs/health.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

LOG_FILE = "/home/openclaw/FinRobot/logs/daemon.log"
STATE_FILE = "/home/openclaw/FinRobot/state/moonshot/state.json"
POSITIONS_FILE = "/home/openclaw/FinRobot/state/moonshot/positions.json"
MAX_LOG_STALENESS = 120


def check_process_running():
    try:
        result = subprocess.run(
            ["pgrep", "-f", "moonshot.daemon.main"],
            capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split('\n') if result.stdout.strip() else []
        return len(pids) > 0, pids
    except Exception as e:
        logger.error(f"Error checking process: {e}")
        return False, []


def check_log_staleness():
    try:
        if not os.path.exists(LOG_FILE):
            return False, "Log file not found"
        mtime = os.path.getmtime(LOG_FILE)
        age = time.time() - mtime
        if age > MAX_LOG_STALENESS:
            return False, f"Log stale ({age:.0f}s old, max {MAX_LOG_STALENESS}s)"
        return True, f"Log fresh ({age:.0f}s old)"
    except Exception as e:
        return False, f"Error checking log: {e}"


def check_state_health():
    try:
        if not os.path.exists(STATE_FILE):
            return True, "No state file yet"
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        balance = state.get('balance', 0)
        if balance < 1.0:
            return False, f"Balance too low: {balance:.2f}"
        return True, f"Balance: {balance:.2f}"
    except Exception as e:
        return False, f"State error: {e}"


def check_positions_health():
    try:
        if not os.path.exists(POSITIONS_FILE):
            return True, "No positions"
        with open(POSITIONS_FILE, 'r') as f:
            positions = json.load(f)
        now = time.time()
        stale_positions = []
        for symbol, pos in positions.items():
            open_time = pos.get('open_time', now)
            age = now - open_time
            if age > 3600:
                stale_positions.append(f"{symbol}({age:.0f}s)")
        if stale_positions:
            return False, f"Stale positions: {', '.join(stale_positions)}"
        return True, f"{len(positions)} positions OK"
    except Exception as e:
        return True, f"Positions check skipped: {e}"


def restart_daemon():
    logger.warning("Attempting daemon restart...")
    try:
        subprocess.run(["pkill", "-f", "moonshot.daemon.main"], timeout=10)
        time.sleep(3)
    except Exception:
        pass

    try:
        subprocess.run(
            ["systemctl", "--user", "restart", "moonshot-daemon.service"],
            timeout=15, capture_output=True
        )
        logger.info("Restarted via systemd")
    except Exception:
        logger.warning("Systemd restart failed, trying direct launch...")
        try:
            subprocess.Popen(
                ["nohup", "python3", "/home/openclaw/FinRobot/scripts/run_daemon.py",
                 "--interval", "15", "--balance", "100"],
                stdout=open('/home/openclaw/FinRobot/logs/daemon.log', 'a'),
                stderr=subprocess.STDOUT,
                cwd="/home/openclaw/FinRobot",
                start_new_session=True,
            )
            logger.info("Restarted via nohup")
        except Exception as e:
            logger.error(f"Failed to restart daemon: {e}")
            return False
    return True


def run_health_check():
    checks = {
        "process": check_process_running(),
        "log_staleness": check_log_staleness(),
        "state_health": check_state_health(),
        "positions_health": check_positions_health(),
    }

    all_healthy = True
    for name, (ok, msg) in checks.items():
        status = "OK" if ok else "FAIL"
        logger.info(f"  [{status}] {name}: {msg}")
        if not ok:
            all_healthy = False

    return all_healthy, checks


def main():
    logger.info("=" * 50)
    logger.info("Moonshot Daemon Health Check")
    logger.info("=" * 50)

    healthy, checks = run_health_check()

    if not healthy:
        logger.warning("Health check FAILED - attempting restart")
        success = restart_daemon()
        if success:
            time.sleep(10)
            running, pids = check_process_running()
            if running:
                logger.info(f"Daemon restarted successfully (PIDs: {pids})")
            else:
                logger.error("Daemon restart FAILED - manual intervention needed")
        else:
            logger.error("Could not restart daemon")
    else:
        logger.info("All health checks passed")

    logger.info("")

    if len(sys.argv) > 1 and sys.argv[1] == "--watch":
        logger.info("Entering watch mode (checking every 60s)...")
        while True:
            time.sleep(60)
            healthy, _ = run_health_check()
            if not healthy:
                logger.warning("Watchdog triggered - restarting...")
                restart_daemon()


if __name__ == "__main__":
    main()
