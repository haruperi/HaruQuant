"""01_breakout_runner.py"""
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
from apps.backtest import EventDrivenEngine
from data.strategies.edge.01_breakout import BreakoutStrategy
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def main():
    logger.info("Starting 01 Breakout Strategy Backtest...")
    # ... Implementation similar to 03_pending_backtest.py ...
