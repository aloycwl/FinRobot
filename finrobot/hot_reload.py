from __future__ import annotations

import os
import sys
import importlib
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger("hot_reload")


class StrategyHotReloader:
    def __init__(self):
        self.strategy_files = [
            "finrobot.grid",
            "finrobot.backtesting",
            "finrobot.hft",
            "finrobot.config"
        ]
        self.file_mtimes: Dict[str, float] = {}
        self.backup_dir = "/home/openclaw/FinRobot/strategy_backups"
        os.makedirs(self.backup_dir, exist_ok=True)
        self.check_mtimes()

    def check_mtimes(self) -> None:
        """Record last modified times for all strategy files"""
        for module_name in self.strategy_files:
            try:
                module = sys.modules.get(module_name)
                if module and hasattr(module, '__file__') and module.__file__:
                    self.file_mtimes[module_name] = os.path.getmtime(module.__file__)
            except Exception:
                pass

    def has_changes(self) -> bool:
        """Check if any strategy file has been modified"""
        for module_name in self.strategy_files:
            try:
                module = sys.modules.get(module_name)
                if module and hasattr(module, '__file__') and module.__file__:
                    current_mtime = os.path.getmtime(module.__file__)
                    if module_name in self.file_mtimes and current_mtime > self.file_mtimes[module_name]:
                        logger.info(f"Strategy file modified: {module_name}")
                        return True
            except Exception:
                continue
        return False

    def backup_current(self) -> str:
        """Backup current strategy state"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.backup_dir, f"strategy_backup_{timestamp}")
        os.makedirs(backup_path, exist_ok=True)

        for module_name in self.strategy_files:
            try:
                module = sys.modules.get(module_name)
                if module and hasattr(module, '__file__') and module.__file__:
                    import shutil
                    shutil.copy2(module.__file__, backup_path)
            except Exception:
                pass

        logger.info(f"Strategy backed up to {backup_path}")
        return backup_path

    def reload_strategies(self) -> bool:
        """Hot reload all strategy modules"""
        logger.info("Reloading strategy modules")

        self.backup_current()

        success = True
        for module_name in self.strategy_files:
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                    logger.debug(f"Reloaded {module_name}")
            except Exception as e:
                logger.error(f"Failed to reload {module_name}: {str(e)}")
                success = False

        self.check_mtimes()

        if success:
            logger.info("All strategies reloaded successfully")
        return success


def reload_all_modules() -> bool:
    """Public entry point to reload all strategy modules (imported from feedback_loop)"""
    reloader = StrategyHotReloader()
    return reloader.reload_strategies()
