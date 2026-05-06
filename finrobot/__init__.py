"""
FinRobot - Self-Improving Autonomous Algorithmic Trading System
"""

__version__ = "1.0.0"
__author__ = "FinRobot Team"

# Import main components for easy access
from finrobot.utils.config import settings
from finrobot.utils.logging_config import setup_logging, get_logger

__all__ = [
    "settings",
    "setup_logging",
    "get_logger",
]
