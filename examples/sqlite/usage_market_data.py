"""
Usage examples for apps.sqlite.market_data.py

This module demonstrates:
- MarketDataManager class for market data metadata
- Saving market data metadata
- Retrieving market data list
"""

from apps.sqlite import SQLiteDatabase
from datetime import datetime


def example_save_market_data_metadata():
    """
    Example: Save metadata for downloaded market data

    Metadata includes:
    - Symbol and timeframe
    - Source (MT5, CSV, API, etc.)
    - Date range and record count
    - Validation report
    - File path to the actual data
    """
    db = SQLiteDatabase(db_path="test_market_data.db")
    db.initialize_database()

    # Save metadata for EURUSD H1 data
    data_id = db.save_market_data_metadata({
        "symbol": "EURUSD",
        "timeframe": "H1",
        "source": "MT5",
        "start_date": "2023-01-01 00:00:00",
        "end_date": "2023-12-31 23:00:00",
        "record_count": 8760,
        "validation_report": {
            "missing_bars": 0,
            "duplicates": 0,
            "gaps": [],
            "quality_score": 100.0
        },
        "file_path": "data/market/EURUSD_H1_2023.csv"
    })
    print(f"Market data metadata saved with ID: {data_id}")

    # Save metadata for multiple symbols
    symbols = ["GBPUSD", "USDJPY", "AUDUSD"]
    for symbol in symbols:
        data_id = db.save_market_data_metadata({
            "symbol": symbol,
            "timeframe": "H4",
            "source": "MT5",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "record_count": 2190,
            "file_path": f"data/market/{symbol}_H4_2023.csv"
        })
        print(f"  {symbol} metadata saved with ID: {data_id}")


def example_validation_report():
    """
    Example: Storing validation report with market data

    Validation reports help track data quality:
    - Missing bars
    - Duplicate records
    - Data gaps
    - Quality metrics
    """
    db = SQLiteDatabase(db_path="test_validation.db")
    db.initialize_database()

    # Comprehensive validation report
    validation_report = {
        "missing_bars": 5,
        "duplicates": 0,
        "gaps": [
            {"start": "2023-03-15 10:00:00", "end": "2023-03-15 15:00:00"},
            {"start": "2023-07-20 08:00:00", "end": "2023-07-20 09:00:00"}
        ],
        "quality_score": 99.4,
        "checked_at": str(datetime.now()),
        "validation_rules": [
            "no_future_dates",
            "monotonic_timestamps",
            "positive_prices",
            "reasonable_spread"
        ]
    }

    data_id = db.save_market_data_metadata({
        "symbol": "EURUSD",
        "timeframe": "M15",
        "source": "API",
        "start_date": "2023-06-01",
        "end_date": "2023-06-30",
        "record_count": 2880,
        "validation_report": validation_report,
        "file_path": "data/market/EURUSD_M15_202306.parquet"
    })

    print(f"Market data with validation report saved: {data_id}")
    print(f"  Quality score: {validation_report['quality_score']}%")
    print(f"  Missing bars: {validation_report['missing_bars']}")
    print(f"  Data gaps: {len(validation_report['gaps'])}")


def example_get_market_data_list():
    """
    Example: Retrieve list of all market data

    Returns all market data records sorted by creation date (newest first).
    """
    db = SQLiteDatabase(db_path="test_list.db")
    db.initialize_database()

    # Add several market data entries
    datasets = [
        {"symbol": "EURUSD", "timeframe": "H1", "source": "MT5", "file_path": "data/EURUSD_H1.csv"},
        {"symbol": "EURUSD", "timeframe": "H4", "source": "MT5", "file_path": "data/EURUSD_H4.csv"},
        {"symbol": "GBPUSD", "timeframe": "H1", "source": "MT5", "file_path": "data/GBPUSD_H1.csv"},
        {"symbol": "USDJPY", "timeframe": "D1", "source": "API", "file_path": "data/USDJPY_D1.csv"},
    ]

    for dataset in datasets:
        dataset.update({
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "record_count": 8000
        })
        db.save_market_data_metadata(dataset)

    # Retrieve all market data
    all_data = db.get_market_data_list()

    print(f"Total market data entries: {len(all_data)}")
    print("\nMarket data list:")
    for data in all_data:
        print(f"  ID {data['id']}: {data['symbol']} {data['timeframe']} "
              f"({data['source']}) - {data['record_count']} records")


def example_multiple_timeframes():
    """
    Example: Managing multiple timeframes for same symbol

    Shows how to organize market data for different timeframes.
    """
    db = SQLiteDatabase(db_path="test_timeframes.db")
    db.initialize_database()

    symbol = "EURUSD"
    timeframes = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
    record_counts = [525600, 105120, 35040, 17520, 8760, 2190, 365]

    print(f"Saving {symbol} data for multiple timeframes:")
    for timeframe, count in zip(timeframes, record_counts):
        data_id = db.save_market_data_metadata({
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "MT5",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "record_count": count,
            "file_path": f"data/market/{symbol}_{timeframe}_2023.csv"
        })
        print(f"  {timeframe}: {count} bars (ID: {data_id})")

    # Retrieve and display all timeframes
    all_data = db.get_market_data_list()
    eurusd_data = [d for d in all_data if d['symbol'] == symbol]
    print(f"\nTotal timeframes for {symbol}: {len(eurusd_data)}")


def example_data_sources():
    """
    Example: Tracking data from different sources

    Shows how to manage data from multiple sources:
    - MT5 (MetaTrader 5)
    - CSV files
    - APIs (Alpha Vantage, Yahoo Finance, etc.)
    - Other brokers
    """
    db = SQLiteDatabase(db_path="test_sources.db")
    db.initialize_database()

    sources_data = [
        {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "source": "MT5",
            "file_path": "data/mt5/EURUSD_H1.csv"
        },
        {
            "symbol": "EURUSD",
            "timeframe": "H1",
            "source": "AlphaVantage",
            "file_path": "data/api/EURUSD_H1_av.csv"
        },
        {
            "symbol": "EURUSD",
            "timeframe": "D1",
            "source": "YahooFinance",
            "file_path": "data/api/EURUSD_D1_yf.csv"
        },
        {
            "symbol": "BTCUSD",
            "timeframe": "H1",
            "source": "Binance",
            "file_path": "data/crypto/BTCUSD_H1.parquet"
        }
    ]

    print("Saving data from multiple sources:")
    for data in sources_data:
        data.update({
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "record_count": 8000
        })
        data_id = db.save_market_data_metadata(data)
        print(f"  {data['symbol']} from {data['source']}: ID {data_id}")


def example_datetime_handling():
    """
    Example: Different datetime format handling

    Shows how to save metadata with various datetime formats.
    """
    db = SQLiteDatabase(db_path="test_datetime.db")
    db.initialize_database()

    # String format
    db.save_market_data_metadata({
        "symbol": "EURUSD",
        "timeframe": "H1",
        "source": "MT5",
        "start_date": "2023-01-01 00:00:00",
        "end_date": "2023-12-31 23:00:00",
        "record_count": 8760,
        "file_path": "data/test1.csv"
    })
    print("Saved with string datetime")

    # Datetime object
    db.save_market_data_metadata({
        "symbol": "GBPUSD",
        "timeframe": "H1",
        "source": "MT5",
        "start_date": datetime(2023, 1, 1),
        "end_date": datetime(2023, 12, 31),
        "record_count": 8760,
        "file_path": "data/test2.csv"
    })
    print("Saved with datetime objects")

    # ISO format string
    db.save_market_data_metadata({
        "symbol": "USDJPY",
        "timeframe": "H1",
        "source": "MT5",
        "start_date": "2023-01-01T00:00:00Z",
        "end_date": "2023-12-31T23:00:00Z",
        "record_count": 8760,
        "file_path": "data/test3.csv"
    })
    print("Saved with ISO format datetime")


def example_complete_workflow():
    """
    Example: Complete market data workflow

    Shows typical workflow:
    1. Download data from source
    2. Validate data
    3. Save data to file
    4. Save metadata to database
    5. Retrieve metadata when needed
    """
    db = SQLiteDatabase(db_path="test_workflow.db")
    db.initialize_database()

    print("Step 1: Download data from MT5")
    symbol = "EURUSD"
    timeframe = "H1"
    print(f"  Downloading {symbol} {timeframe}...")

    print("\nStep 2: Validate data")
    validation = {
        "missing_bars": 0,
        "duplicates": 0,
        "quality_score": 100.0
    }
    print(f"  Quality score: {validation['quality_score']}%")

    print("\nStep 3: Save data to file")
    file_path = f"data/market/{symbol}_{timeframe}_2023.csv"
    print(f"  Saved to: {file_path}")

    print("\nStep 4: Save metadata to database")
    data_id = db.save_market_data_metadata({
        "symbol": symbol,
        "timeframe": timeframe,
        "source": "MT5",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "record_count": 8760,
        "validation_report": validation,
        "file_path": file_path
    })
    print(f"  Metadata ID: {data_id}")

    print("\nStep 5: Retrieve metadata when needed")
    all_data = db.get_market_data_list()
    for data in all_data:
        if data['id'] == data_id:
            print(f"  Symbol: {data['symbol']}")
            print(f"  Timeframe: {data['timeframe']}")
            print(f"  Records: {data['record_count']}")
            print(f"  File: {data['file_path']}")
            print(f"  Quality: {data['validation_report']['quality_score']}%")


if __name__ == "__main__":
    print("=" * 80)
    print("MarketDataManager Usage Examples")
    print("=" * 80)

    print("\n1. Save Market Data Metadata")
    print("-" * 80)
    example_save_market_data_metadata()

    print("\n2. Validation Report")
    print("-" * 80)
    example_validation_report()

    print("\n3. Get Market Data List")
    print("-" * 80)
    example_get_market_data_list()

    print("\n4. Multiple Timeframes")
    print("-" * 80)
    example_multiple_timeframes()

    print("\n5. Data Sources")
    print("-" * 80)
    example_data_sources()

    print("\n6. Datetime Handling")
    print("-" * 80)
    example_datetime_handling()

    print("\n7. Complete Workflow")
    print("-" * 80)
    example_complete_workflow()
