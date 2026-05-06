#!/usr/bin/env python3
"""
EMERGENCY OPENCODE TRIGGER

This script immediately triggers Opencode to fix critical issues:
1. Grid strategy: 0 trades in 2,400+ iterations
2. HFT strategy: 0 trades in 2,400+ iterations  
3. Martingale strategy: Consistently losing (20% win rate)
"""

import subprocess
import sys
import os
from datetime import datetime

# Setup consolidated logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finrobot.utils.logging_config import setup_logging, get_logger
setup_logging()
logger = get_logger("emergency_fix")

# Configuration
OPENCODE_BIN = "/home/openclaw/.npm-global/bin/opencode"
PROJECT_ROOT = "/home/openclaw/FinRobot"

def build_emergency_prompt() -> str:
    """Build emergency prompt for Opencode with specific fixes needed."""
    
    prompt = f"""
🚨 EMERGENCY: Trading Strategies Completely Broken After 2,400+ Iterations 🚨

TIME: {datetime.utcnow().isoformat()}
STATUS: CRITICAL - All strategies failing

═══════════════════════════════════════════════════════════════

❌ CRITICAL ISSUE #1: GRID STRATEGY - ZERO TRADES
   - Iterations tested: 2,400+
   - Total trades: 0
   - Return: 0.00%
   - Win rate: 0.00%
   - Best parameters: grid_step_pips=1.0, take_profit_pips=3.0, max_grid_levels=2
   - LAST UPDATED: 2026-05-01 (3 DAYS AGO!)

   🔧 REQUIRED FIXES:
   1. grid_step_pips is TOO LARGE for XAUUSD volatility
      - Current: 1.0 pips
      - Try: 0.1, 0.25, 0.5 pips first
   
   2. Add DEBUG LOGGING to show why orders aren't placed:
      - Log current price vs grid levels
      - Log trend direction on every bar
      - Log when price crosses grid boundaries
   
   3. Verify data column names match expectations:
      - Check if 'close' column exists
      - Check if 'time' column is datetime
      - Add error handling for missing columns

❌ CRITICAL ISSUE #2: HFT STRATEGY - ZERO TRADES
   - Iterations tested: 2,400+
   - Total trades: 0
   - Return: 0.00%
   - Win rate: 0.00%
   - Best parameters: tick_threshold=0.08, volume_filter=10, spread_limit=0.01
   - LAST UPDATED: 2026-05-01 (3 DAYS AGO!)

   🔧 REQUIRED FIXES:
   1. tick_threshold is TOO HIGH for XAUUSD on 1m timeframe
      - Current: 0.08 (8% move required!)
      - XAUUSD typical 1m move: 0.001-0.01 (0.1% to 1%)
      - Try: 0.001, 0.002, 0.005
   
   2. volume_filter may be too restrictive:
      - Current: 10
      - Try: 1, 2, 5 (especially for XAUUSD)
   
   3. spread_limit may be too tight:
      - Current: 0.01 (1%)
      - Try: 0.05, 0.1 (5%, 10%)
   
   4. Add DEBUG MODE to log every signal generation:
      - Log price changes vs threshold
      - Log volume vs filter
      - Log when signals are blocked by spread

❌ CRITICAL ISSUE #3: MARTINGALE STRATEGY - CONSISTENTLY LOSING
   - Iterations tested: 2,400+
   - Total trades: 7,629
   - Return: -0.99%
   - Win rate: 19.9% (BELOW 55% TARGET!)
   - Best parameters: multiplier=1.25, base_lot=0.005, max_steps=2, ema_fast=8, ema_slow=34
   - LAST UPDATED: 2026-05-01 (3 DAYS AGO!)

   🔧 REQUIRED FIXES:
   1. Win rate is FAR BELOW 55% target (currently 19.9%)
      - Strategy is essentially random/gambling
      - Need MAJOR algorithm changes
   
   2. EMA periods may be too slow:
      - Current: 8/34
      - Try: 3/8, 5/13 for faster signals
   
   3. Multiplier may still be too aggressive:
      - Current: 1.25x
      - Try: 1.1x, 1.15x (less aggressive martingale)
   
   4. ADD STOP LOSSES immediately:
      - Current: NO stop loss (infinite risk!)
      - Add: 2% stop loss per trade
      - Add: 5% daily loss limit
   
   5. Consider completely different approach:
      - Current: Martingale on trend following (not working)
      - Try: Mean reversion with Bollinger Bands
      - Try: Breakout strategy with volume confirmation
      - Try: Multiple timeframe confirmation

═══════════════════════════════════════════════════════════════

📊 SYSTEM METRICS SUMMARY:
   - Daemon running: 1,077+ minutes
   - Current iteration: 2,386 / 10,000 (23.8%)
   - Strategies tested: 3 (Grid, Martingale, HFT)
   - Working strategies: 0
   - Profitable strategies: 0
   - Best performer: Grid (0% return, 0 trades)

🚨 EMERGENCY STATUS: CRITICAL
   All strategies failing after 2,400+ iterations.
   System requires IMMEDIATE intervention.

═══════════════════════════════════════════════════════════════

🔧 IMMEDIATE ACTIONS REQUIRED:

1. Fix Grid strategy grid_step_pips (1.0 → 0.1-0.5 range)
2. Fix HFT strategy tick_threshold (0.08 → 0.001-0.01 range)
3. Add stop losses to Martingale strategy
4. Add debug logging to all strategies
5. Test completely new strategy types (breakout, mean reversion)

YOU MUST MAKE ACTUAL CODE CHANGES - NOT JUST SUGGESTIONS.
Modify the files directly and test your changes.

TARGET: 5% hourly return, 85% win rate, <1.5% max drawdown
CURRENT: 0% return, 0-20% win rate, unknown drawdown

═══════════════════════════════════════════════════════════════
"""
    
    return prompt

def trigger_emergency_opencode():
    """Trigger Opencode with emergency prompt."""
    
    print("🚨 EMERGENCY OPENCODE TRIGGER 🚨")
    print("=" * 60)
    print(f"Time: {datetime.utcnow().isoformat()}")
    print("=" * 60)
    
    # Build emergency prompt
    prompt = build_emergency_prompt()
    
    print(f"\n📋 Prompt length: {len(prompt)} characters")
    print("📝 First 500 chars of prompt:")
    print(prompt[:500])
    print("\n... [truncated for display] ...\n")
    
    # Trigger Opencode
    try:
        print("🚀 Triggering Opencode...")
        
        cmd = [
            OPENCODE_BIN,
            "run",
            "--continue",
            prompt
        ]
        
        # Set environment
        env = os.environ.copy()
        env["PATH"] = f"{os.path.dirname(OPENCODE_BIN)}:{env['PATH']}"
        env["OPENCODE_MODEL"] = "kimi-k2.5"
        
        print(f"   Command: {' '.join(cmd[:3])} ... [prompt truncated]")
        print(f"   Working directory: {PROJECT_ROOT}")
        print(f"   Timeout: 600 seconds")
        
        # Execute with timeout
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
            env=env
        )
        
        logger.info(f"Opencode execution completed - exit code: {result.returncode}")
        
        # Log results to consolidated log
        logger.info(f"Opencode stdout length: {len(result.stdout)} chars")
        logger.info(f"Opencode stderr length: {len(result.stderr)} chars")
        
        if result.returncode == 0:
            logger.info("SUCCESS: Opencode completed successfully! The strategies should now be fixed.")
            return 0
        else:
            logger.warning(f"Opencode exited with code {result.returncode}")
            return 1
            
    except subprocess.TimeoutExpired:
        logger.error("Opencode timed out after 600 seconds")
        return 1
    except Exception as e:
        logger.error(f"Failed to trigger Opencode: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(trigger_emergency_opencode())