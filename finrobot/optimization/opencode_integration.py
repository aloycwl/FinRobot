"""
Opencode Integration - FIXED VERSION

This module provides integration with Opencode AI for automatic strategy improvement.
It uses a direct subprocess call to opencode with a properly structured prompt.

Key fixes:
1. Correct opencode CLI invocation
2. Proper prompt structure
3. Automatic file modification capability
4. Clear instructions for the AI
"""

from __future__ import annotations

import os
import json
import time
import subprocess
import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


class NumpyJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyJsonEncoder, self).default(obj)

logger = logging.getLogger("opencode_feedback")


class OpencodeFeedbackLoop:
    """
    Fixed Opencode feedback loop that actually calls opencode and gets code improvements.
    """
    
    def __init__(self):
        self.last_call: Optional[datetime] = None
        self.min_interval = timedelta(minutes=75)  # 75 minute minimum between calls
        self.opencode_bin = "/home/openclaw/.npm-global/bin/opencode"
        self.project_root = "/home/openclaw/FinRobot"
        self.feedback_log = "/home/openclaw/FinRobot/opencode_feedback.log"
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(self.feedback_log), exist_ok=True)

    def can_call(self) -> bool:
        """Check rate limit before calling opencode."""
        if not self.last_call:
            return True
        return datetime.utcnow() - self.last_call > self.min_interval

    def build_prompt(self, metrics: Dict[str, Any], logs: str) -> str:
        """Build structured prompt for opencode agent with CLEAR instructions to modify code."""
        
        # Get current strategy file contents
        strategy_files = self._get_strategy_files()
        
        prompt = f"""
=== AUTOMATIC STRATEGY IMPROVEMENT REQUEST ===
Time: {datetime.utcnow().isoformat()}

CURRENT PERFORMANCE METRICS:
{json.dumps(metrics, indent=2, cls=NumpyJsonEncoder)}

STRATEGY FILES TO MODIFY:
{strategy_files}

INSTRUCTIONS - YOU MUST MODIFY THE CODE DIRECTLY:

1. ANALYZE the performance metrics above
2. IDENTIFY what's causing poor performance (low win rate, high drawdown, etc.)
3. MODIFY the strategy code in the files listed above
4. TEST your changes by improving:
   - Win rate (target: >55%)
   - Reduce drawdown (target: <2%)
   - Increase total return (target: >5%)

SPECIFIC CHANGES TO MAKE:
- Adjust entry/exit logic
- Modify indicator parameters (EMA periods, ADX thresholds, etc.)
- Fix position sizing
- Add better stop-loss / take-profit logic
- Implement trend filters

YOU ARE ALLOWED TO:
- Edit any file in finrobot/strategies/
- Modify function parameters
- Add new indicators
- Change logic completely
- Delete code that doesn't work

YOU MUST:
- Make ACTUAL code changes (not suggestions)
- Save the modified files
- Ensure the code is valid Python
- Keep the same function signatures for backtest compatibility

=== END OF REQUEST ===
"""
        return prompt

    def _get_strategy_files(self) -> str:
        """Get list of strategy files that can be modified."""
        strategy_dir = "/home/openclaw/FinRobot/finrobot/strategies"
        files = []
        
        if os.path.exists(strategy_dir):
            for f in os.listdir(strategy_dir):
                if f.endswith('.py') and not f.startswith('__'):
                    files.append(f"- finrobot/strategies/{f}")
        
        # Also include new strategies
        new_strategies_dir = "/home/openclaw/FinRobot/finrobot/strategies/new_strategies"
        if os.path.exists(new_strategies_dir):
            for f in os.listdir(new_strategies_dir):
                if f.endswith('.py') and not f.startswith('__'):
                    files.append(f"- finrobot/strategies/new_strategies/{f}")
        
        return "\n".join(files) if files else "- finrobot/strategies/grid.py\n- finrobot/strategies/backtesting.py"

    def send_feedback(self, metrics: Dict[str, Any], logs: str) -> bool:
        """
        Send feedback to opencode agent to improve strategy.
        This is the KEY function that actually calls opencode.
        """
        if not self.can_call():
            logger.debug("Rate limit active, skipping opencode call")
            return False

        logger.info("🤖 Calling opencode for strategy improvement...")
        prompt = self.build_prompt(metrics, logs)

        try:
            # Use opencode run command with proper arguments
            # The prompt is passed as a file to avoid command line length issues
            prompt_file = "/tmp/opencode_prompt.txt"
            with open(prompt_file, "w") as f:
                f.write(prompt)
            
            cmd = [
                self.opencode_bin,
                "run",
                "--file", prompt_file,
                "--no-confirm"  # Auto-execute without user confirmation
            ]

            logger.info(f"Executing: {' '.join(cmd)}")

            env = os.environ.copy()
            env["PATH"] = f"{os.path.dirname(self.opencode_bin)}:{env['PATH']}"
            env["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "")
            env["ANTHROPIC_API_KEY"] = os.environ.get("ANTHROPIC_API_KEY", "")

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env=env
            )

            self.last_call = datetime.utcnow()

            # Log the result
            log_entry = f"""
{'='*60}
OPENCODE FEEDBACK - {self.last_call.isoformat()}
{'='*60}
Exit Code: {result.returncode}
Duration: ~{(datetime.utcnow() - self.last_call).total_seconds() + 600:.0f}s

STDOUT:
{result.stdout}

STDERR:
{result.stderr}
{'='*60}
"""
            with open(self.feedback_log, "a") as f:
                f.write(log_entry)

            if result.returncode == 0:
                logger.info("✅ Opencode completed successfully - strategies should be improved")
                return True
            else:
                logger.error(f"❌ Opencode failed with exit code {result.returncode}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("❌ Opencode timed out after 10 minutes")
            self.last_call = datetime.utcnow()
            return False
        except Exception as e:
            logger.error(f"❌ Failed to call opencode: {str(e)}", exc_info=True)
            self.last_call = datetime.utcnow()
            return False

    def should_trigger(self, metrics: Dict[str, Any]) -> bool:
        """Decide if we should trigger an improvement request."""
        # Trigger on bad performance
        win_rate = metrics.get("win_rate", 1.0)
        max_drawdown = metrics.get("max_drawdown", 0.0)
        
        if win_rate < 0.55:
            logger.info(f"🚨 Triggering feedback: Win rate {win_rate:.1%} below 55% threshold")
            return True

        if max_drawdown < -0.02:
            logger.info(f"🚨 Triggering feedback: Drawdown {max_drawdown:.1%} exceeds -2% threshold")
            return True

        # Regular scheduled optimization every 24h
        if not self.last_call or datetime.utcnow() - self.last_call > timedelta(hours=24):
            logger.info("📅 Triggering scheduled 24h optimization")
            return True

        return False
