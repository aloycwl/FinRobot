#!/usr/bin/env python3
"""
Improved Opencode Integration with Comprehensive Testing Framework

This module provides:
1. Automatic trigger detection for Opencode feedback
2. Comprehensive testing scenario management
3. Smart prompt building based on actual performance issues
4. Rate limiting and cooldown management
"""

from __future__ import annotations

import os
import sys
import json
import time
import subprocess
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path

# Setup consolidated logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from finrobot.utils.logging_config import get_logger

from finrobot.testing_scenarios import (
    TriggerCondition,
    TriggerConfig,
    TRIGGER_CONFIGS,
    build_opencode_prompt,
    generate_all_scenarios,
    TestingScenario
)


logger = get_logger("opencode_integration")


class NumpyJsonEncoder(json.JSONEncoder):
    """Handle numpy types for JSON serialization."""
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NumpyJsonEncoder, self).default(obj)


class ComprehensiveFeedbackLoop:
    """
    Comprehensive feedback loop with intelligent triggering and testing scenarios.
    """
    
    def __init__(self):
        self.opencode_bin = "/home/openclaw/.npm-global/bin/opencode"
        self.project_root = "/home/openclaw/FinRobot"
        # No separate feedback log - all logging goes to finrobot.log
        self.trigger_history_file = "/home/openclaw/FinRobot/trigger_history.json"
        
        # Track last trigger times for rate limiting
        self.last_trigger_times: Dict[TriggerCondition, datetime] = {}
        
        # Load scenarios
        self.scenarios = generate_all_scenarios()
        
        # Load trigger history
        self._load_trigger_history()
        
        logger.info(f"Comprehensive feedback loop initialized with {len(self.scenarios)} scenarios")
    
    def _load_trigger_history(self):
        """Load trigger history from file."""
        if os.path.exists(self.trigger_history_file):
            try:
                with open(self.trigger_history_file, 'r') as f:
                    data = json.load(f)
                    for key, timestamp in data.items():
                        try:
                            self.last_trigger_times[TriggerCondition(key)] = datetime.fromisoformat(timestamp)
                        except:
                            pass
            except Exception as e:
                logger.warning(f"Could not load trigger history: {e}")
    
    def _save_trigger_history(self):
        """Save trigger history to file."""
        try:
            data = {
                key.value: timestamp.isoformat()
                for key, timestamp in self.last_trigger_times.items()
            }
            with open(self.trigger_history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save trigger history: {e}")
    
    def check_trigger(self, 
                     condition: TriggerCondition,
                     metrics: Dict[str, Any],
                     iteration: int) -> bool:
        """
        Check if a specific trigger condition is met.
        
        Returns True if trigger should fire.
        """
        config = TRIGGER_CONFIGS.get(condition)
        if not config or not config.enabled:
            return False
        
        # Check minimum iterations
        if iteration < config.min_iterations:
            return False
        
        # Check cooldown
        last_trigger = self.last_trigger_times.get(condition)
        if last_trigger:
            cooldown = timedelta(minutes=config.cooldown_minutes)
            if datetime.utcnow() - last_trigger < cooldown:
                return False
        
        # Check threshold condition
        metric_value = None
        
        if condition == TriggerCondition.WIN_RATE_LOW:
            metric_value = metrics.get('win_rate', 1.0)
            if metric_value < config.threshold:
                logger.warning(f"Trigger {condition.value}: Win rate {metric_value:.1%} < {config.threshold:.1%}")
                return True
                
        elif condition == TriggerCondition.DRAWDOWN_HIGH:
            metric_value = metrics.get('max_drawdown', 0.0)
            if metric_value < config.threshold:  # threshold is negative
                logger.warning(f"Trigger {condition.value}: Drawdown {metric_value:.1%} < {config.threshold:.1%}")
                return True
                
        elif condition == TriggerCondition.NO_TRADES:
            metric_value = metrics.get('total_trades', 0)
            if metric_value <= config.threshold and iteration > 100:
                logger.warning(f"Trigger {condition.value}: No trades after {iteration} iterations")
                return True
                
        elif condition == TriggerCondition.HIGH_FAILURE_RATE:
            metric_value = metrics.get('failure_rate', 0.0)
            if metric_value > config.threshold:
                logger.warning(f"Trigger {condition.value}: Failure rate {metric_value:.0%} > {config.threshold:.0%}")
                return True
                
        elif condition == TriggerCondition.NO_WORKING_STRATEGIES:
            working = metrics.get('working_strategies', 0)
            if working <= config.threshold and iteration >= config.min_iterations:
                logger.warning(f"Trigger {condition.value}: No working strategies after {iteration} iterations")
                return True
                
        elif condition == TriggerCondition.RETURN_NEGATIVE:
            ret = metrics.get('total_return', 0.0)
            if ret < config.threshold:
                logger.warning(f"Trigger {condition.value}: Return {ret:.1%} < {config.threshold:.1%}")
                return True
                
        elif condition == TriggerCondition.SCHEDULED_24H:
            # Always trigger if cooldown has passed
            return True
            
        elif condition == TriggerCondition.SCHEDULED_500_ITERATIONS:
            if iteration % 500 == 0 and iteration > 0:
                return True
                
        elif condition == TriggerCondition.TARGET_MET:
            ret = metrics.get('total_return', 0.0)
            if ret >= config.threshold:
                logger.info(f"Trigger {condition.value}: Target return {ret:.1%} achieved!")
                return True
        
        return False
    
    def check_all_triggers(self, 
                          metrics: Dict[str, Any],
                          iteration: int) -> List[Tuple[TriggerCondition, str]]:
        """
        Check all trigger conditions and return list of fired triggers.
        
        Returns list of (condition, reason) tuples.
        """
        fired_triggers = []
        
        for condition in TriggerCondition:
            if self.check_trigger(condition, metrics, iteration):
                reason = f"Condition {condition.value} met at iteration {iteration}"
                fired_triggers.append((condition, reason))
                # Record trigger time
                self.last_trigger_times[condition] = datetime.utcnow()
        
        # Save trigger history
        if fired_triggers:
            self._save_trigger_history()
        
        return fired_triggers
    
    def call_opencode(self,
                     trigger: TriggerCondition,
                     reason: str,
                     metrics: Dict[str, Any],
                     logs: str) -> bool:
        """
        Call Opencode with comprehensive prompt.
        
        Returns True if successful.
        """
        logger.info(f"Calling Opencode for trigger: {trigger.value}")
        
        # Build comprehensive prompt
        prompt = build_opencode_prompt(trigger, metrics, logs)
        
        # Add trigger-specific context
        prompt += f"""

TRIGGER DETAILS:
- Condition: {trigger.value}
- Reason: {reason}
- Timestamp: {datetime.utcnow().isoformat()}
- Severity: {TRIGGER_CONFIGS[trigger].severity if trigger in TRIGGER_CONFIGS else 'unknown'}

ADDITIONAL CONTEXT:
This is an automated request from the FinRobot trading system. The daemon has been running 
continuous backtests and detected the above issue. Please analyze the metrics and logs, then 
make actual code changes to improve the strategy performance.

PRIORITY ACTIONS:
1. Fix any bugs causing zero trades or high failure rates
2. Optimize parameters based on the failing metrics
3. Add new indicators or filters to improve performance
4. Ensure all changes are syntactically correct and tested

Remember: Target metrics are 5% hourly return, 85% win rate, <1.5% max drawdown.
"""
        
        try:
            # Prepare command
            cmd = [
                self.opencode_bin,
                "run",
                "--continue",
                prompt
            ]
            
            # Set up environment
            env = os.environ.copy()
            env["PATH"] = f"{os.path.dirname(self.opencode_bin)}:{env['PATH']}"
            env["OPENCODE_MODEL"] = "kimi-k2.5"  # Use your custom model
            
            logger.info(f"Executing opencode command (timeout: 600s)")
            
            # Execute with timeout
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600,
                env=env
            )
            
            # Log results
            log_entry = f"""
===== OPENCODE FEEDBACK {datetime.utcnow().isoformat()} =====
TRIGGER: {trigger.value}
EXIT CODE: {result.returncode}
STDOUT:
{result.stdout}
STDERR:
{result.stderr}
PROMPT_LENGTH: {len(prompt)} characters
==================================================
"""
            
            with open(self.feedback_log, "a") as f:
                f.write(log_entry)
            
            if result.returncode == 0:
                logger.info(f"✅ Opencode completed successfully for trigger {trigger.value}")
                return True
            else:
                logger.error(f"❌ Opencode failed with code {result.returncode}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Opencode timed out after 600 seconds")
            return False
        except Exception as e:
            logger.error(f"💥 Failed to call opencode: {str(e)}", exc_info=True)
            return False
    
    def run_feedback_cycle(self, metrics: Dict[str, Any], logs: str, iteration: int) -> List[str]:
        """
        Run a complete feedback cycle: check triggers and call Opencode if needed.
        
        Returns list of actions taken.
        """
        actions = []
        
        # Check all triggers
        fired_triggers = self.check_all_triggers(metrics, iteration)
        
        if not fired_triggers:
            actions.append("No triggers fired")
            return actions
        
        # Process each fired trigger
        for trigger, reason in fired_triggers:
            actions.append(f"Trigger fired: {trigger.value}")
            
            # Call Opencode
            success = self.call_opencode(trigger, reason, metrics, logs)
            
            if success:
                actions.append(f"✅ Opencode call successful for {trigger.value}")
            else:
                actions.append(f"❌ Opencode call failed for {trigger.value}")
        
        return actions


# Global instance for easy access
_feedback_loop_instance: Optional[ComprehensiveFeedbackLoop] = None


def get_feedback_loop() -> ComprehensiveFeedbackLoop:
    """Get or create the global feedback loop instance."""
    global _feedback_loop_instance
    if _feedback_loop_instance is None:
        _feedback_loop_instance = ComprehensiveFeedbackLoop()
    return _feedback_loop_instance


if __name__ == "__main__":
    # Test the feedback loop
    print("Testing comprehensive feedback loop...")
    
    loop = get_feedback_loop()
    
    # Test metrics
    test_metrics = {
        "win_rate": 0.45,
        "max_drawdown": -0.025,
        "total_return": -0.03,
        "total_trades": 0,
        "failure_rate": 0.85,
        "working_strategies": 0,
        "total_iterations": 150
    }
    
    # Test logs
    test_logs = "Sample log entries...\nMore logs...\n"
    
    # Run feedback cycle
    actions = loop.run_feedback_cycle(test_metrics, test_logs, 150)
    
    print("\nActions taken:")
    for action in actions:
        print(f"  - {action}")