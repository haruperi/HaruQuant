"""09_trend_following_ma_runner.py"""
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

from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
from apps.simulation.utils import calculate_metrics_from_simulator
from apps.mt5.client import MT5Client
from apps.sqlite.users import UserManager
from apps.utils.logger import logger
from apps.utils.logger import logger

module_name = "09_trend_following_ma"
file_path = project_root / "data/strategies/edge/09_trend_following_ma.py"
spec = importlib.util.spec_from_file_location(module_name, file_path)
module = importlib.util.module_from_spec(spec)
sys.modules[module_name] = module
spec.loader.exec_module(module)
TrendFollowingMAStrategy = module.TrendFollowingMAStrategy

def get_mt5_client():
    """Get a connected MT5 client."""
    creds = UserManager().get_mt5_credentials()
    client = MT5Client()
    if not client.connect(creds["path"], creds["login"], creds["password"], creds["server"]):
        raise ConnectionError("Failed to connect to MT5")
    return client

def load_mt5_data(symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    client = get_mt5_client()
    try:
        df = client.get_bars(symbol=symbol, timeframe=timeframe, date_from=date_from, date_to=date_to)
        if df is None or df.empty:
            raise ValueError("No data retrieved from MT5")
        return df
    finally:
        client.shutdown()

def main():
    logger.info("Starting 09 Trend Following MA Strategy Backtest...")
    backtest_start = datetime(2025, 1, 1)
    backtest_end = datetime(2025, 12, 31)
    data_load_start = backtest_start - timedelta(days=250)
    
    try:
        data = load_mt5_data('EURUSD', 'D1', data_load_start, backtest_end)
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return

    strategy = TrendFollowingMAStrategy(params={'symbol': 'EURUSD'})

    # Initialize strategy
    strategy.on_init()

    # Calculate signals
    data = strategy.on_bar(data)

    # Get MT5 client for symbol info
    mt5_client = get_mt5_client()

    # Setup simulator components
    account_info = AccountInfoSimulator(
        balance=10000.0,
        equity=10000.0,
        margin_free=10000.0,
    )
    symbol_info = SymbolInfoSimulator.from_mt5_symbol('EURUSD')
    symbol_info.symbol = 'EURUSD'

    # Create simulator
    simulator = TradeSimulator(
        simulator_name="TrendFollowingMA_Backtest",
        mt5_client=mt5_client,
        account_info=account_info,
        symbols={'EURUSD': symbol_info},
    )

    # Run simulation
    simulator.run(
        data=data,
        strategy=strategy,
        symbol='EURUSD',
        volume=0.1,
        verbose=False,
        save_db=False,
        engine_type="event_driven",
        commission_per_contract=7.0,
        slippage_points=0,
        start_date=backtest_start,
        end_date=backtest_end,
    )

    # Get results from simulator
    result = calculate_metrics_from_simulator(simulator)

    display_metrics(result)

    # Cleanup
    mt5_client.shutdown()
if __name__ == "__main__":
    main()

