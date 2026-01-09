import sys
import os
import time
from datetime import datetime

# Add project root to path
# Assuming this file is in tests/usage/mt5/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from apps.mt5.client import MT5Client
from apps.logger import logger
from apps.sqlite.users import UserManager

def main():
    # Initialize UserManager and get credentials
    # Defaults to 'haruperi' and uses centralized db_path
    creds = UserManager().get_mt5_credentials()
    
    if not creds:
        logger.error("No default broker credentials found")
        return

    logger.info(f"Using credentials for account: {creds['login']} on {creds['server']}")

def on_tick_data(tick_data):
    """Callback for tick data."""
    # tick_data is a dictionary
    print(f"[{datetime.now().strftime('%H:%M:%S')}] TICK  - {tick_data['symbol']} | Bid: {tick_data['bid']:.5f} | Ask: {tick_data['ask']:.5f}")

def on_bar_data(bar_data):
    """Callback for bar data."""
    # bar_data is a pandas Series (last row of DataFrame)
    # The name of the series is the timestamp
    print(f"[{datetime.now().strftime('%H:%M:%S')}] BAR   - {bar_data.name} | Close: {bar_data['close']:.5f} | Vol: {bar_data['volume']}")

    # Initialize client with credentials
    client = MT5Client(
        login=creds["login"],
        password=creds["password"],
        server=creds["server"],
        path=creds["path"],
        timeout=60000,
        portable=False
    )
    
    if not client.is_connected():
        logger.error("Failed to connect to MT5")
        return

    symbol = "EURUSD"
    
    try:
        logger.info(f"Starting streaming demonstration for {symbol}...")
        
        # 1. Start Tick Streaming
        logger.info("Subscribing to Ticks...")
        client.start_streaming(symbol, "ticks", on_tick_data)
        
        # 2. Start Bar Streaming (e.g., M1 bars, checking every 5 seconds)
        logger.info("Subscribing to M1 Bars...")
        client.start_streaming(
            symbol, 
            "bars", 
            on_bar_data, 
            interval=5.0,  # Poll every 5 seconds
            timeframe="M1"
        )
        
        print("\nStreaming started. Press Ctrl+C to stop.\n")
        
        # Keep main thread running
        # In a real app, this might be your main event loop or strategy engine
        start_time = time.time()
        while time.time() - start_time < 30: # Run for 30 seconds for demo
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping...")
    except Exception as e:
        logger.error(f"Error during execution: {e}")
    finally:
        # Cleanup
        logger.info("Stopping streams...")
        client.stop_streaming(symbol, "ticks")
        client.stop_streaming(symbol, "bars")
        
        logger.info("Shutting down client...")
        client.shutdown()

if __name__ == "__main__":
    main()
