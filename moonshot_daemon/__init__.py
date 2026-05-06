"""
Moonshot Daemon Package
24/7 Automated Trading Bot for Hyperliquid
"""

__version__ = "1.0.0"
__author__ = "Moonshot Team"

# Import main components
from .hyperliquid_ws_client import HyperliquidWebSocketClient, create_websocket_client
from .state_manager import StateManager, PositionState, TradeRecord

__all__ = [
    'HyperliquidWebSocketClient',
    'create_websocket_client',
    'StateManager',
    'PositionState',
    'TradeRecord',
]