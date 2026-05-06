#!/usr/bin/env python3
"""
Comprehensive Testing Scenarios Framework for FinRobot

This module defines all testing scenarios, parameter ranges, and feedback triggers
for the Opencode feedback loop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import numpy as np


class MarketCondition(Enum):
    """Different market conditions to test under."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    OPENING_SESSION = "opening_session"
    CLOSING_SESSION = "closing_session"


class TriggerCondition(Enum):
    """Conditions that trigger Opencode feedback."""
    WIN_RATE_LOW = "win_rate_below_55"
    DRAWDOWN_HIGH = "drawdown_above_2pct"
    NO_TRADES = "zero_trades_for_100_iterations"
    HIGH_FAILURE_RATE = "failure_rate_above_80pct"
    NO_WORKING_STRATEGIES = "no_working_strategies_after_10_iterations"
    RETURN_NEGATIVE = "return_below_minus_5pct"
    SCHEDULED_24H = "scheduled_24h"
    SCHEDULED_500_ITERATIONS = "scheduled_500_iterations"
    TARGET_MET = "target_5pct_return_achieved"


@dataclass
class ParameterRange:
    """Defines a parameter range with testing strategy."""
    name: str
    values: List[Any]
    priority: int = 5  # 1 = highest, 10 = lowest
    current_best: Optional[Any] = None
    
    def get_test_values(self, mode: str = "grid") -> List[Any]:
        """Get values to test based on mode."""
        if mode == "grid":
            return self.values
        elif mode == "random":
            return [np.random.choice(self.values)]
        elif mode == "best":
            if self.current_best is not None:
                # Test best and neighbors
                idx = self.values.index(self.current_best) if self.current_best in self.values else len(self.values) // 2
                start = max(0, idx - 1)
                end = min(len(self.values), idx + 2)
                return self.values[start:end]
            return self.values[:3]  # Test first 3 if no best known
        return self.values


@dataclass
class StrategyTestConfig:
    """Complete testing configuration for a strategy."""
    name: str
    description: str
    parameter_ranges: Dict[str, ParameterRange]
    target_return: float = 0.05  # 5% hourly
    target_win_rate: float = 0.85  # 85%
    max_drawdown: float = 0.015  # 1.5%
    min_trades: int = 10
    market_conditions: List[MarketCondition] = field(default_factory=lambda: [
        MarketCondition.TRENDING_UP,
        MarketCondition.RANGE_BOUND,
        MarketCondition.HIGH_VOLATILITY
    ])
    
    def get_parameter_combinations(self, max_tests: int = 100) -> List[Dict[str, Any]]:
        """Generate parameter combinations to test."""
        import itertools
        
        # Sort by priority
        sorted_params = sorted(
            self.parameter_ranges.items(),
            key=lambda x: x[1].priority
        )
        
        # Get test values for each parameter
        test_values = []
        for name, param_range in sorted_params:
            values = param_range.get_test_values(mode="best")
            test_values.append([(name, v) for v in values])
        
        # Generate combinations
        combinations = []
        for combo in itertools.product(*test_values):
            param_dict = {name: value for name, value in combo}
            combinations.append(param_dict)
            if len(combinations) >= max_tests:
                break
        
        return combinations


@dataclass
class TestingScenario:
    """A specific testing scenario with expected outcomes."""
    name: str
    description: str
    strategy_config: StrategyTestConfig
    market_condition: MarketCondition
    data_requirements: Dict[str, Any]
    expected_outcomes: Dict[str, tuple]  # metric -> (min, max, target)
    
    def evaluate_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate test results against expected outcomes."""
        evaluation = {
            "passed": True,
            "metrics": {},
            "score": 0.0,
            "recommendations": []
        }
        
        for metric, (min_val, max_val, target) in self.expected_outcomes.items():
            actual = results.get(metric, 0)
            metric_eval = {
                "actual": actual,
                "target": target,
                "min_acceptable": min_val,
                "max_acceptable": max_val,
                "status": "unknown"
            }
            
            if actual < min_val:
                metric_eval["status"] = "below_minimum"
                evaluation["passed"] = False
                evaluation["recommendations"].append(f"{metric}: Increase from {actual:.2%} to at least {min_val:.2%}")
            elif actual > max_val:
                metric_eval["status"] = "above_maximum"
                evaluation["passed"] = False
                evaluation["recommendations"].append(f"{metric}: Decrease from {actual:.2%} to at most {max_val:.2%}")
            else:
                metric_eval["status"] = "acceptable"
                # Calculate score based on proximity to target
                if target != 0:
                    score_contrib = 1.0 - abs(actual - target) / abs(target)
                    evaluation["score"] += max(0, score_contrib) / len(self.expected_outcomes)
            
            evaluation["metrics"][metric] = metric_eval
        
        return evaluation


# ============================================================================
# COMPREHENSIVE TESTING CONFIGURATIONS
# ============================================================================

GRID_TESTING_CONFIG = StrategyTestConfig(
    name="Grid Trading",
    description="Grid trading strategy for XAUUSD with dynamic spacing",
    parameter_ranges={
        "grid_step_pips": ParameterRange(
            "grid_step_pips",
            [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0, 20.0],
            priority=1
        ),
        "take_profit_pips": ParameterRange(
            "take_profit_pips",
            [0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0],
            priority=1
        ),
        "trend_ema_fast": ParameterRange(
            "trend_ema_fast",
            [3, 5, 8, 12, 21, 34],
            priority=3
        ),
        "trend_ema_slow": ParameterRange(
            "trend_ema_slow",
            [8, 15, 21, 34, 55, 89],
            priority=3
        ),
        "max_grid_levels": ParameterRange(
            "max_grid_levels",
            [1, 2, 3, 5, 8, 12, 20, 50],
            priority=2
        ),
        "base_lot": ParameterRange(
            "base_lot",
            [0.001, 0.005, 0.01, 0.02, 0.05, 0.1],
            priority=4
        ),
        "fee_bps": ParameterRange(
            "fee_bps",
            [0.1, 0.5, 1.0, 2.0, 3.0, 5.0],
            priority=5
        ),
    },
    market_conditions=[
        MarketCondition.RANGE_BOUND,
        MarketCondition.TRENDING_UP,
        MarketCondition.TRENDING_DOWN,
        MarketCondition.LOW_VOLATILITY
    ]
)

MARTINGALE_TESTING_CONFIG = StrategyTestConfig(
    name="Martingale Trend Following",
    description="Martingale with trend confirmation using EMA crossovers",
    parameter_ranges={
        "multiplier": ParameterRange(
            "multiplier",
            [1.05, 1.1, 1.15, 1.2, 1.25, 1.5, 1.75, 2.0, 2.5],
            priority=1
        ),
        "base_lot": ParameterRange(
            "base_lot",
            [0.001, 0.005, 0.01, 0.02, 0.03, 0.05],
            priority=3
        ),
        "max_steps": ParameterRange(
            "max_steps",
            [1, 2, 3, 4, 5, 6, 8, 10],
            priority=1
        ),
        "ema_fast": ParameterRange(
            "ema_fast",
            [2, 3, 5, 8, 12, 15],
            priority=2
        ),
        "ema_slow": ParameterRange(
            "ema_slow",
            [8, 12, 15, 20, 34, 55],
            priority=2
        ),
        "stop_loss_pct": ParameterRange(
            "stop_loss_pct",
            [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5],
            priority=1
        ),
        "take_profit_pct": ParameterRange(
            "take_profit_pct",
            [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5],
            priority=1
        ),
        "adx_filter": ParameterRange(
            "adx_filter",
            [0, 10, 15, 20, 25, 30, 40],
            priority=4
        ),
    },
    market_conditions=[
        MarketCondition.TRENDING_UP,
        MarketCondition.TRENDING_DOWN,
        MarketCondition.HIGH_VOLATILITY
    ]
)

HFT_TESTING_CONFIG = StrategyTestConfig(
    name="High Frequency Trading",
    description="Microsecond-level scalping based on order flow and momentum",
    parameter_ranges={
        "tick_threshold": ParameterRange(
            "tick_threshold",
            [0.001, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.1, 0.15, 0.2],
            priority=1
        ),
        "volume_filter": ParameterRange(
            "volume_filter",
            [1, 5, 10, 25, 50, 100, 200, 500],
            priority=3
        ),
        "latency_ms": ParameterRange(
            "latency_ms",
            [1, 10, 25, 50, 100, 200, 500],
            priority=4
        ),
        "spread_limit": ParameterRange(
            "spread_limit",
            [0.001, 0.005, 0.01, 0.02, 0.03, 0.05, 0.1],
            priority=2
        ),
        "fast_window": ParameterRange(
            "fast_window",
            [1, 2, 3, 5, 8],
            priority=3
        ),
        "slow_window": ParameterRange(
            "slow_window",
            [5, 8, 12, 20, 34],
            priority=3
        ),
        "min_hold_time_ms": ParameterRange(
            "min_hold_time_ms",
            [0, 100, 500, 1000, 5000, 10000],
            priority=5
        ),
        "max_hold_time_ms": ParameterRange(
            "max_hold_time_ms",
            [1000, 5000, 10000, 30000, 60000, 300000],
            priority=5
        ),
        "profit_target_ticks": ParameterRange(
            "profit_target_ticks",
            [1, 2, 3, 5, 8, 13, 21],
            priority=2
        ),
        "stop_loss_ticks": ParameterRange(
            "stop_loss_ticks",
            [1, 2, 3, 5, 8, 13, 21, 34],
            priority=2
        ),
    },
    market_conditions=[
        MarketCondition.HIGH_VOLATILITY,
        MarketCondition.RANGE_BOUND,
        MarketCondition.TRENDING_UP,
        MarketCondition.TRENDING_DOWN
    ]
)


# ============================================================================
# TRIGGER CONFIGURATION
# ============================================================================

@dataclass
class TriggerConfig:
    """Configuration for when to trigger Opencode feedback."""
    enabled: bool = True
    threshold: float = 0.0
    min_iterations: int = 10
    cooldown_minutes: int = 75
    severity: str = "warning"  # info, warning, critical


TRIGGER_CONFIGS = {
    TriggerCondition.WIN_RATE_LOW: TriggerConfig(
        enabled=True,
        threshold=0.55,
        min_iterations=50,
        cooldown_minutes=75,
        severity="critical"
    ),
    TriggerCondition.DRAWDOWN_HIGH: TriggerConfig(
        enabled=True,
        threshold=-0.02,
        min_iterations=20,
        cooldown_minutes=60,
        severity="critical"
    ),
    TriggerCondition.NO_TRADES: TriggerConfig(
        enabled=True,
        threshold=0,
        min_iterations=100,
        cooldown_minutes=120,
        severity="warning"
    ),
    TriggerCondition.HIGH_FAILURE_RATE: TriggerConfig(
        enabled=True,
        threshold=0.8,
        min_iterations=50,
        cooldown_minutes=60,
        severity="warning"
    ),
    TriggerCondition.NO_WORKING_STRATEGIES: TriggerConfig(
        enabled=True,
        threshold=0,
        min_iterations=10,
        cooldown_minutes=30,
        severity="critical"
    ),
    TriggerCondition.RETURN_NEGATIVE: TriggerConfig(
        enabled=True,
        threshold=-0.05,
        min_iterations=30,
        cooldown_minutes=90,
        severity="warning"
    ),
    TriggerCondition.SCHEDULED_24H: TriggerConfig(
        enabled=True,
        threshold=0,
        min_iterations=0,
        cooldown_minutes=1440,
        severity="info"
    ),
    TriggerCondition.SCHEDULED_500_ITERATIONS: TriggerConfig(
        enabled=True,
        threshold=0,
        min_iterations=500,
        cooldown_minutes=60,
        severity="info"
    ),
    TriggerCondition.TARGET_MET: TriggerConfig(
        enabled=True,
        threshold=0.05,
        min_iterations=50,
        cooldown_minutes=240,
        severity="info"
    ),
}


# ============================================================================
# SCENARIO GENERATOR
# ============================================================================

def generate_all_scenarios() -> List[TestingScenario]:
    """Generate all testing scenarios for comprehensive testing."""
    scenarios = []
    
    # Grid scenarios
    for condition in GRID_TESTING_CONFIG.market_conditions:
        scenario = TestingScenario(
            name=f"Grid_{condition.value}",
            description=f"Grid trading under {condition.value} conditions",
            strategy_config=GRID_TESTING_CONFIG,
            market_condition=condition,
            data_requirements={
                "min_bars": 1000,
                "timeframe": "1m",
                "volatility_range": (0.1, 2.0)
            },
            expected_outcomes={
                "total_return": (0.0, 0.20, 0.05),
                "win_rate": (0.50, 1.0, 0.85),
                "max_drawdown": (-0.05, 0.0, -0.015),
                "total_trades": (10, 10000, 100)
            }
        )
        scenarios.append(scenario)
    
    # Martingale scenarios
    for condition in MARTINGALE_TESTING_CONFIG.market_conditions:
        scenario = TestingScenario(
            name=f"Martingale_{condition.value}",
            description=f"Martingale trend following under {condition.value} conditions",
            strategy_config=MARTINGALE_TESTING_CONFIG,
            market_condition=condition,
            data_requirements={
                "min_bars": 5000,
                "timeframe": "1m",
                "trend_strength": "strong" if "trending" in condition.value else "weak"
            },
            expected_outcomes={
                "total_return": (0.0, 0.20, 0.05),
                "win_rate": (0.50, 1.0, 0.85),
                "max_drawdown": (-0.05, 0.0, -0.015),
                "total_trades": (10, 10000, 100)
            }
        )
        scenarios.append(scenario)
    
    # HFT scenarios
    for condition in HFT_TESTING_CONFIG.market_conditions:
        scenario = TestingScenario(
            name=f"HFT_{condition.value}",
            description=f"High frequency trading under {condition.value} conditions",
            strategy_config=HFT_TESTING_CONFIG,
            market_condition=condition,
            data_requirements={
                "min_bars": 10000,
                "timeframe": "1m",
                "tick_data": True
            },
            expected_outcomes={
                "total_return": (0.0, 0.20, 0.05),
                "win_rate": (0.50, 1.0, 0.85),
                "max_drawdown": (-0.05, 0.0, -0.015),
                "num_trades": (100, 100000, 1000)
            }
        )
        scenarios.append(scenario)
    
    return scenarios


# ============================================================================
# OPENCODE FEEDBACK PROMPT BUILDER
# ============================================================================

def build_opencode_prompt(
    trigger_condition: TriggerCondition,
    metrics: Dict[str, Any],
    logs: str,
    scenario_results: List[TestingScenario] = None
) -> str:
    """Build a comprehensive prompt for Opencode based on trigger condition."""
    
    base_prompt = f"""
=== FINROBOT AUTOMATIC STRATEGY OPTIMIZATION REQUEST ===
Trigger: {trigger_condition.value}
Time: {datetime.now().isoformat()}
Iteration: {metrics.get('total_iterations', 'N/A')}

CURRENT PERFORMANCE METRICS:
{json.dumps(metrics, indent=2, default=str)}

CRITICAL ISSUES DETECTED:
"""
    
    # Add specific issues based on trigger
    if trigger_condition == TriggerCondition.WIN_RATE_LOW:
        base_prompt += f"""
- Win rate is {metrics.get('win_rate', 0):.1%}, which is below the 55% minimum threshold
- This indicates the strategy is taking too many losing trades
- Possible causes: poor entry timing, weak trend filtering, or unsuitable market conditions

REQUIRED FIXES:
1. Add stronger trend confirmation (ADX > 25 requirement)
2. Implement volume confirmation (minimum 1.5x average)
3. Add support/resistance filtering (don't trade into S/R levels)
4. Test different EMA combinations (faster signals)
5. Implement time-based filters (avoid low-volume periods)
"""
    
    elif trigger_condition == TriggerCondition.NO_TRADES:
        base_prompt += f"""
- Strategy has executed 0 trades for over 100 iterations
- This indicates the entry conditions are too restrictive or there's a bug
- Possible causes: incorrect price data, wrong column names, or impossible conditions

REQUIRED FIXES:
1. Add detailed debug logging showing why each trade was rejected
2. Verify price column names match the data source (close vs Close vs close_price)
3. Check if grid_step_pips is appropriate for XAUUSD volatility
4. Ensure volume data is available and correctly formatted
5. Add minimum price movement detection
6. Test with ultra-low thresholds (grid_step_pips=0.1) to verify execution
"""
    
    elif trigger_condition == TriggerCondition.NO_WORKING_STRATEGIES:
        base_prompt += f"""
- No strategies are working after 10+ iterations
- All strategies are failing to produce positive returns
- This is a CRITICAL situation requiring immediate architectural changes

REQUIRED FIXES:
1. Implement completely new strategy types:
   - Breakout strategy (Bollinger Band squeeze + volume spike)
   - Mean reversion (RSI oversold/overbought with divergence)
   - Trend following with multi-timeframe confirmation
   - Volume-based strategy (volume profile + POC)
   
2. Add new technical indicators:
   - ADX for trend strength (require ADX > 25 for trend trades)
   - Ichimoku Cloud (support/resistance + trend direction)
   - Bollinger Bands (volatility + mean reversion)
   - RSI with divergence detection
   - MACD with histogram analysis
   
3. Implement risk management:
   - Maximum daily loss limit (stop trading after -2%)
   - Position sizing based on volatility (Kelly criterion)
   - Correlation filtering (avoid correlated pairs)
   - Time-based stops (close before weekends/news)
"""
    
    # Add logs section
    base_prompt += f"""

RECENT BACKTEST LOGS:
{logs[-5000:]}

INSTRUCTIONS FOR OPENCODE:
1. Make ACTUAL CODE CHANGES - don't just give suggestions
2. Test your changes by running a quick backtest mentally
3. Focus on the highest impact changes first
4. Keep changes minimal but effective
5. Ensure code is syntactically correct Python
6. Add comments explaining WHY you made each change

TARGET METRICS TO ACHIEVE:
- Return: 5%+ hourly
- Win Rate: 85%+
- Max Drawdown: <1.5%
- Trades: Minimum 10 per test

Modify these files as needed:
- finrobot/grid.py (Grid strategy)
- finrobot/backtesting.py (Martingale strategy)
- finrobot/hft.py (HFT strategy)
- finrobot/indicators.py (Technical indicators)
- finrobot/config.py (Configuration)
"""
    
    return base_prompt


# Export all configurations
__all__ = [
    'MarketCondition',
    'TriggerCondition',
    'ParameterRange',
    'StrategyTestConfig',
    'TestingScenario',
    'TriggerConfig',
    'GRID_TESTING_CONFIG',
    'MARTINGALE_TESTING_CONFIG',
    'HFT_TESTING_CONFIG',
    'TRIGGER_CONFIGS',
    'generate_all_scenarios',
    'build_opencode_prompt'
]