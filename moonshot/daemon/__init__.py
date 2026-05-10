"""
Moonshot Daemon Package
24/7 Automated Trading Bot for Hyperliquid with Self-Improvement
"""

__version__ = "2.0.0"
__author__ = "Moonshot Team"

from .hyperliquid_ws_client import HyperliquidWebSocketClient, create_websocket_client
from .state_manager import StateManager, PositionState, TradeRecord
from .self_improvement import (
    StrategyPerformanceTracker,
    ParameterOptimizer,
    SelfImprover,
    OpencodeFeedback,
)

__all__ = [
    'HyperliquidWebSocketClient',
    'create_websocket_client',
    'StateManager',
    'PositionState',
    'TradeRecord',
    'StrategyPerformanceTracker',
    'ParameterOptimizer',
    'SelfImprover',
    'OpencodeFeedback',
]