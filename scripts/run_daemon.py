#!/usr/bin/env python3
"""
Moonshot 24/7 Daemon Launcher
Simple launcher for the 24/7 trading daemon
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from moonshot.daemon.main import main

if __name__ == "__main__":
    main()
