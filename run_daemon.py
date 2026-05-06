#!/usr/bin/env python3
"""
Moonshot 24/7 Daemon Launcher
Simple launcher for the 24/7 trading daemon
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from moonshot_daemon.main import main

if __name__ == "__main__":
    main()