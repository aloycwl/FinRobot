#!/usr/bin/env python3
"""
Consolidated Logging Configuration for FinRobot

All logging goes to a single file: /home/openclaw/FinRobot/finrobot.log

Usage:
    from finrobot.logging_config import setup_logging, get_logger
    
    setup_logging()
    logger = get_logger("my_module")
    logger.info("Message here")
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# Single log file for everything
LOG_FILE = "/home/openclaw/FinRobot/finrobot.log"
MAX_BYTES = 50 * 1024 * 1024  # 50MB
BACKUP_COUNT = 3

# Track if logging has been set up
_logging_configured = False


def setup_logging(level=logging.INFO):
    """Setup consolidated logging to single file."""
    global _logging_configured
    
    if _logging_configured:
        return
    
    # Ensure log directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Rotating file handler
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    
    # Console handler (optional, for debugging)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    _logging_configured = True
    
    # Log that logging is set up
    logger = logging.getLogger("logging_config")
    logger.info(f"Logging initialized - all output to: {LOG_FILE}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name."""
    if not _logging_configured:
        setup_logging()
    return logging.getLogger(name)


def cleanup_old_logs():
    """Remove old log files that are no longer used."""
    old_logs = [
        "/home/openclaw/FinRobot/trading_daemon.log",
        "/home/openclaw/FinRobot/feedback_iterations.log",
        "/home/openclaw/FinRobot/emergency_opencode.log",
        "/home/openclaw/FinRobot/opencode_feedback.log",
        "/home/openclaw/FinRobot/backtest_logs/backtest_engine.log",
        "/home/openclaw/FinRobot/backtest_logs/console.log",
        "/home/openclaw/FinRobot/multi_strategy.log",
    ]
    
    removed = []
    for log_file in old_logs:
        if os.path.exists(log_file):
            try:
                os.remove(log_file)
                removed.append(log_file)
            except Exception as e:
                print(f"Failed to remove {log_file}: {e}")
    
    if removed:
        print(f"Cleaned up {len(removed)} old log files")
    
    return removed


if __name__ == "__main__":
    setup_logging()
    logger = get_logger("test")
    logger.info("Test message")
    print(f"Log file: {LOG_FILE}")
