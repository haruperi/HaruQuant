"""04_extended_mean_reversion_runner.py"""
import sys
import importlib.util
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

try:
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    # Import metrics utils from the same directory
    sys.path.insert(0, str(current_file.parent))
    from metrics_utils import display_metrics
except Exception as e:
    print(f"Error setting up path: {e}")
    sys.exit(1)

from apps.backtest import EventDrivenEngine
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.logger import logger
from apps.logger import logger

module_name = "04_extended_mean_reversion"
file_path = project_root / "data/strategies/edge/04_extended_mean_reversion.py"
spec = importlib.util.spec_from_file_location(module_name, file_path)
module = importlib.util.module_from_spec(spec)
sys.modules[module_name] = module
spec.loader.exec_module(module)
ExtendedMeanReversionStrategy = module.ExtendedMeanReversionStrategy

def load_mt5_data(symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    creds = UserManager().get_mt5_credentials()
    with MT5Client(login=creds["login"], password=creds["password"], server=creds["server"], path=creds["path"]) as client:
        return client.get_bars(symbol=symbol, timeframe=timeframe, date_from=date_from, date_to=date_to)

def main():
    logger.info("Starting 04 Extended Mean Reversion Strategy Backtest...")
    backtest_start = datetime(2025, 1, 1)
    backtest_end = datetime(2025, 12, 31)
    data_load_start = backtest_start - timedelta(days=250)
    
    try:
        data = load_mt5_data('EURUSD', 'D1', data_load_start, backtest_end)
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return

    strategy = ExtendedMeanReversionStrategy(params={'symbol': 'EURUSD'})
    engine = EventDrivenEngine(strategy=strategy, data=data, initial_balance=10000.0, backtest_start_date=backtest_start, backtest_end_date=backtest_end, timeframe='D1')
    result = engine.run()
    
    display_metrics(result)

if __name__ == "__main__":
    main()
