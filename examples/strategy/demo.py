import sys
import os

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from datetime import datetime, timedelta
from apps.sqlite.users import UserManager
from apps.utils.logger import logger
from data.strategies.trend_following import TrendFollowingStrategy
from apps.mt5 import MT5Client, get_mt5_api
mt5 = get_mt5_api()


def get_mt5_credentials():
    """Get MT5 credentials from the database."""
    creds = UserManager().get_mt5_credentials()
    if not creds:
        logger.error("No default broker credentials found")
        sys.exit(1)
    return creds


def main():
    """Main function to run the strategy."""

    # Get credentials from database
    creds = get_mt5_credentials()

    # Initialize MT5 client (needed for Option 1)
    client = MT5Client()
    connected = client.connect(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"]
    )

    if not connected:
        logger.error("Failed to connect to MT5. Please ensure MT5 terminal is running.")
        return


    # Get bars
    data = client.get_bars(symbol="EURUSD", timeframe="H1", date_from=datetime(2025, 1, 1), date_to=datetime(2025, 12, 31))

    # Initialize strategy
    strategy = TrendFollowingStrategy(
        params={
            'symbol': 'EURUSD',
            'ema_fast': 20,
            'ema_slow': 50,
            'ema_filter': 200
        }
    )
    
    # Call on_init
    strategy.on_init()
    
    # Calculate indicators and signals (vectorized - happens once)
    print(f"\nCalculating indicators for {len(data)} bars...")
    data = strategy.on_bar(data)
    
    # Check if signal columns were added
    if 'signal' not in data.columns or 'price' not in data.columns:
        print("ERROR: Signal columns (signal, price) not added!")
        return
    
    # Count signals
    buy_signals = (data['signal'] == 'buy').sum()
    sell_signals = (data['signal'] == 'sell').sum()
    total_signals = buy_signals + sell_signals
    
    print(f"\nSignal Summary:")
    print(f"  Total bars: {len(data)}")
    print(f"  Buy signals: {buy_signals}")
    print(f"  Sell signals: {sell_signals}")
    print(f"  Total signals: {total_signals}")
    
    if total_signals == 0:
        print("\nNo signals found in the dataframe.")
        return
    
    # Display all signals
    print(f"\n{'='*80}")
    print("SIGNALS FOUND:")
    print(f"{'='*80}\n")
    
    # Filter to only bars with signals
    signals_df = data[data['signal'].notna()].copy()
    
    for idx, row in signals_df.iterrows():
        signal_info = strategy.get_signal(signals_df, signals_df.index.get_loc(idx))
                
        if signal_info:
            print(f"--- {signal_info['signal']} at {signal_info['time']} ---")
            print(f"  Reason: {signal_info['reason']}")
            print(f"  Order Price: {signal_info['entry_price']:.5f}")
            print() 






if __name__ == "__main__":
    main()

