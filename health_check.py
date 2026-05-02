#!/usr/bin/env python3
"""
Health Check Script for Trading Daemon

This script checks the daemon's health and can be run via cron
to automatically restart the daemon if it fails.

Usage:
    python health_check.py          # Check health and restart if needed
    python health_check.py --status # Just show status
"""

import os
import sys
import subprocess
import json
import argparse
from datetime import datetime, timedelta
import psutil

# Configuration
PROJECT_DIR = "/home/openclaw/FinRobot"
PID_FILE = os.path.join(PROJECT_DIR, "daemon.pid")
STATE_FILE = os.path.join(PROJECT_DIR, "daemon_state.json")
HEALTH_LOG = os.path.join(PROJECT_DIR, "health_check.log")
MAX_STALENESS_MINUTES = 5  # Restart if no update for 5 minutes
MEMORY_THRESHOLD_MB = 500  # Restart if memory exceeds this


def log_message(message: str):
    """Log a message to file and print to stdout."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    
    # Print to stdout
    print(log_line)
    
    # Append to log file
    try:
        with open(HEALTH_LOG, "a") as f:
            f.write(log_line + "\n")
    except Exception as e:
        print(f"Warning: Could not write to health log: {e}")


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_daemon_info() -> dict:
    """Get information about the daemon process."""
    info = {
        "running": False,
        "pid": None,
        "memory_mb": 0,
        "cpu_percent": 0,
        "last_check": None,
        "staleness_minutes": None,
    }
    
    # Check PID file
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
                
            if is_process_running(pid):
                info["running"] = True
                info["pid"] = pid
                
                # Get process info
                try:
                    proc = psutil.Process(pid)
                    info["memory_mb"] = proc.memory_info().rss / 1024 / 1024
                    info["cpu_percent"] = proc.cpu_percent(interval=0.1)
                except:
                    pass
        except (ValueError, IOError):
            pass
    
    # Check state file for last check time
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
                last_check = state.get("last_check")
                if last_check:
                    info["last_check"] = last_check
                    # Calculate staleness
                    try:
                        last_time = datetime.fromisoformat(last_check.replace('Z', '+00:00'))
                        staleness = datetime.now() - last_time.replace(tzinfo=None)
                        info["staleness_minutes"] = staleness.total_seconds() / 60
                    except:
                        pass
        except:
            pass
    
    return info


def show_status():
    """Show daemon status."""
    info = get_daemon_info()
    
    print("\n" + "=" * 60)
    print("Trading Daemon Health Status")
    print("=" * 60)
    
    if info["running"]:
        print(f"✅ Status: RUNNING (PID: {info['pid']})")
        print(f"   Memory: {info['memory_mb']:.1f} MB")
        print(f"   CPU: {info['cpu_percent']:.1f}%")
    else:
        print("❌ Status: NOT RUNNING")
    
    if info["last_check"]:
        print(f"\n📅 Last Check: {info['last_check']}")
        if info["staleness_minutes"] is not None:
            stale_text = f"{info['staleness_minutes']:.1f} minutes ago"
            if info["staleness_minutes"] > MAX_STALENESS_MINUTES:
                print(f"   ⚠️  STALE: {stale_text} (threshold: {MAX_STALENESS_MINUTES} min)")
            else:
                print(f"   ✅ Fresh: {stale_text}")
    
    print("=" * 60 + "\n")


def restart_daemon():
    """Restart the daemon."""
    log_message("Restarting daemon...")
    
    # Stop if running
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            if is_process_running(pid):
                log_message(f"Stopping existing daemon (PID: {pid})...")
                os.kill(pid, 15)  # SIGTERM
                # Wait for process to stop
                for _ in range(10):
                    if not is_process_running(pid):
                        break
                    import time
                    time.sleep(0.5)
                # Force kill if still running
                if is_process_running(pid):
                    os.kill(pid, 9)  # SIGKILL
        except Exception as e:
            log_message(f"Error stopping daemon: {e}")
    
    # Clean up PID file
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    
    # Start daemon
    log_message("Starting daemon...")
    try:
        # Change to project directory and start
        os.chdir(PROJECT_DIR)
        
        # Start daemon in background
        proc = subprocess.Popen(
            [sys.executable, DAEMON_SCRIPT, "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=PROJECT_DIR,
            start_new_session=True
        )
        
        # Wait a moment and check if it started
        import time
        time.sleep(2)
        
        if is_daemon_running():
            log_message("✅ Daemon started successfully")
            return True
        else:
            log_message("❌ Daemon failed to start")
            return False
            
    except Exception as e:
        log_message(f"❌ Error starting daemon: {e}")
        return False


def is_daemon_running():
    """Check if daemon is currently running."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            return is_process_running(pid)
        except:
            pass
    return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Health Check for Trading Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --status        # Just show status
  %(prog)s                 # Check and restart if needed
  %(prog)s --force-restart # Force restart
        """
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show status only, don't restart"
    )
    parser.add_argument(
        "--force-restart",
        action="store_true",
        help="Force restart even if running"
    )
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
        return
    
    if args.force_restart:
        log_message("Force restart requested")
        restart_daemon()
        return
    
    # Normal health check
    info = get_daemon_info()
    
    needs_restart = False
    
    if not info["running"]:
        log_message("Daemon is not running, will restart")
        needs_restart = True
    elif info["staleness_minutes"] and info["staleness_minutes"] > MAX_STALENESS_MINUTES:
        log_message(f"Daemon appears stale (last check {info['staleness_minutes']:.1f} minutes ago), will restart")
        needs_restart = True
    elif info["memory_mb"] > MEMORY_THRESHOLD_MB:
        log_message(f"Daemon memory usage too high ({info['memory_mb']:.1f}MB), will restart")
        needs_restart = True
    else:
        log_message("Daemon is healthy")
    
    if needs_restart:
        restart_daemon()
    
    # Show final status
    show_status()


if __name__ == "__main__":
    main()
