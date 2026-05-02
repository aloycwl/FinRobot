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
    def __init__(self):
        self.last_call: Optional[datetime] = None
        self.min_interval = timedelta(minutes=75)
        self.opencode_bin = "/home/openclaw/.npm-global/bin/opencode"
        self.project_root = "."
        self.feedback_log = "./opencode_feedback.log"

    def can_call(self) -> bool:
        """Check rate limit before calling opencode"""
        if not self.last_call:
            return True
        return datetime.utcnow() - self.last_call > self.min_interval

    def build_prompt(self, metrics: Dict[str, Any], logs: str) -> str:
        """Build structured prompt for opencode agent"""
        prompt = f"""
=== AUTOMATIC STRATEGY IMPROVEMENT REQUEST ===
Time: {datetime.utcnow().isoformat()}

CURRENT PERFORMANCE METRICS:
{json.dumps(metrics, indent=2, cls=NumpyJsonEncoder)}

LAST 50 BACKTEST LOG ENTRIES:
{logs[-3000:]}

INSTRUCTIONS:
1. Analyze these performance results
2. TEST ALL INDICATORS: ADX, Ichimoku, Order Blocks, Liquidity Sweeps, FVG, CHoCH, BOS, Fibonacci levels, Divergence
3. Adjust Entry_Score weighting values in indicators.py - test turning on/off individual factors
4. Modify the strategy parameters and logic in grid.py, backtesting.py or hft.py
5. Adjust grid steps, take profit values, EMA periods, martingale ratios
6. Test which indicator combinations give highest win rate
7. Target 5% hourly returns, 85%+ win rate, <1.5% max drawdown

MAKE ACTUAL CODE CHANGES. DO NOT JUST GIVE SUGGESTIONS. MODIFY THE FILES DIRECTLY. YOU CAN CHANGE ANY FILE.
"""
        return prompt

    def send_feedback(self, metrics: Dict[str, Any], logs: str) -> bool:
        """Send feedback to opencode agent to improve strategy"""
        if not self.can_call():
            logger.debug("Rate limit active, skipping opencode call")
            return False

        logger.info("Calling opencode for strategy improvement")
        prompt = self.build_prompt(metrics, logs)

        try:
            cmd = [
                self.opencode_bin,
                "run",
                "--continue",
                prompt
            ]

            env = os.environ.copy()
            env["PATH"] = f"{os.path.dirname(self.opencode_bin)}:{env['PATH']}"

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,
                env=env
            )

            self.last_call = datetime.utcnow()

            log_entry = f"""
===== OPENCODE FEEDBACK {self.last_call.isoformat()} =====
EXIT CODE: {result.returncode}
STDOUT:
{result.stdout}
STDERR:
{result.stderr}
==================================================
"""
            with open(self.feedback_log, "a") as f:
                f.write(log_entry)

            if result.returncode == 0:
                logger.info("Opencode completed successfully")
                return True
            else:
                logger.error(f"Opencode failed with code {result.returncode}")
                return False

        except Exception as e:
            logger.error(f"Failed to call opencode: {str(e)}", exc_info=True)
            return False

    def should_trigger(self, metrics: Dict[str, Any]) -> bool:
        """Decide if we should trigger an improvement request"""
        # Trigger on bad performance
        if metrics.get("win_rate", 1.0) < 0.55:
            logger.info("Triggering feedback: Win rate below 55%")
            return True

        if metrics.get("max_drawdown", 0.0) < -0.02:
            logger.info("Triggering feedback: Drawdown exceeded 2%")
            return True

        # Regular scheduled optimization every 24h
        if not self.last_call or datetime.utcnow() - self.last_call > timedelta(hours=24):
            logger.info("Triggering scheduled optimization")
            return True

        return False
