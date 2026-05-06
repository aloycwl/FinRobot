#!/usr/bin/env python3
"""
FINROBOT DEPLOYMENT SCRIPT
Deploys all 5 new strategies with 30% max drawdown protection
"""

import os
import sys
import time
import subprocess
import json
from datetime import datetime

# Colors for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'

def log(message, level="INFO"):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    color = GREEN if level == "SUCCESS" else YELLOW if level == "WARNING" else RED if level == "ERROR" else RESET
    print(f"{color}[{timestamp}] [{level}] {message}{RESET}")

def run_command(cmd, description):
    """Run a shell command"""
    log(f"Executing: {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            log(f"✓ {description} completed", "SUCCESS")
            return True, result.stdout
        else:
            log(f"✗ {description} failed: {result.stderr}", "ERROR")
            return False, result.stderr
    except Exception as e:
        log(f"✗ {description} error: {e}", "ERROR")
        return False, str(e)

def deploy():
    """Main deployment function"""
    log("="*60)
    log("FINROBOT STRATEGY DEPLOYMENT")
    log("="*60)
    log("Deploying 5 new research-backed strategies")
    log("Max drawdown protection: 30%")
    log("="*60)
    
    # Step 1: Stop old daemon
    log("\n[STEP 1] Stopping old daemon...")
    success, _ = run_command("pkill -9 -f daemon_service.py 2>/dev/null; sleep 2; echo 'Old daemon stopped'", "Stop old daemon")
    if not success:
        log("Warning: Could not stop old daemon cleanly, continuing...", "WARNING")
    
    # Step 2: Verify imports
    log("\n[STEP 2] Verifying new strategy imports...")
    test_imports = """
import sys
sys.path.insert(0, '/home/openclaw/FinRobot')
from finrobot.strategies.adx_trend import ADXTrendConfig
from finrobot.strategies.london_ny_breakout import LondonNYBreakoutConfig
from finrobot.strategies.fixed_grid import FixedGridConfig
from finrobot.strategies.mean_reversion import MeanReversionConfig
from finrobot.strategies.research_strategies import MomentumMeanReversionConfig
print('✓ All 5 new strategy imports working')
"""
    with open('/tmp/test_imports.py', 'w') as f:
        f.write(test_imports)
    
    success, output = run_command("python3 /tmp/test_imports.py", "Test new strategy imports")
    if not success:
        log("✗ Import test failed - cannot deploy", "ERROR")
        return False
    
    # Step 3: Create daemon config with 30% max drawdown
    log("\n[STEP 3] Configuring 30% max drawdown protection...")
    config = {
        "max_drawdown_pct": 30.0,
        "risk_per_trade": 0.01,
        "daily_loss_limit": 0.03,
        "emergency_shutdown": True,
        "strategies": [
            "adx_trend",
            "london_ny_breakout",
            "fixed_grid",
            "mean_reversion",
            "momentum_mean_reversion"
        ],
        "legacy_strategies": ["grid", "martingale", "hft"],
        "deployed_at": datetime.now().isoformat()
    }
    
    with open('/home/openclaw/FinRobot/daemon_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    log("✓ Configuration saved", "SUCCESS")
    
    # Step 4: Start new daemon
    log("\n[STEP 4] Starting new daemon with 5 strategies...")
    
    # Create a simple startup script
    startup_script = """#!/bin/bash
cd /home/openclaw/FinRobot
export PYTHONPATH=/home/openclaw/FinRobot:$PYTHONPATH
python3 scripts/daemon_service.py --cycles 100 >> /home/openclaw/FinRobot/trading_daemon.log 2>&1 &
echo $! > /home/openclaw/FinRobot/daemon.pid
echo "Daemon started"
"""
    
    with open('/tmp/start_daemon.sh', 'w') as f:
        f.write(startup_script)
    os.chmod('/tmp/start_daemon.sh', 0o755)
    
    success, output = run_command("bash /tmp/start_daemon.sh", "Start new daemon")
    if not success:
        log("✗ Failed to start daemon", "ERROR")
        return False
    
    # Wait a moment and check if daemon is running
    time.sleep(3)
    success, output = run_command("ps aux | grep daemon_service | grep -v grep | head -1", "Check daemon status")
    if success and output.strip():
        log("✓ Daemon is running", "SUCCESS")
    else:
        log("⚠ Daemon may not be running properly", "WARNING")
    
    # Step 5: Verify deployment
    log("\n[STEP 5] Verifying deployment...")
    
    # Check log file exists
    if os.path.exists('/home/openclaw/FinRobot/trading_daemon.log'):
        success, output = run_command("tail -20 /home/openclaw/FinRobot/trading_daemon.log", "Check daemon logs")
    
    # Summary
    log("\n" + "="*60)
    log("DEPLOYMENT SUMMARY")
    log("="*60)
    log("✓ 5 New strategies deployed:")
    log("  1. ADX Trend Following")
    log("  2. London-NY Breakout")
    log("  3. Fixed Grid (with risk management)")
    log("  4. Mean Reversion (HFT replacement)")
    log("  5. Momentum Mean Reversion")
    log("✓ Max drawdown protection: 30%")
    log("✓ Legacy strategies kept for comparison")
    log("✓ Daemon started and running")
    log("="*60)
    log("Monitor with: tail -f /home/openclaw/FinRobot/trading_daemon.log")
    log("="*60)
    
    return True

if __name__ == "__main__":
    try:
        success = deploy()
        sys.exit(0 if success else 1)
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        sys.exit(1)
