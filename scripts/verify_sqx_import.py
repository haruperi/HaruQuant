"""Verify SQX import script."""

import os
import sys

import requests

# Ensure we can find the app
sys.path.append(os.getcwd())

API_URL = "http://localhost:8000/api/import/sqx"


def create_dummy_csv():
    """Create a dummy CSV content for testing."""
    # Header based on import_trades.py expectation
    header = "Ticket;Symbol;Type;Result name;Sample type;Comment;Open time;Close time;Time in trade;BarsInTrade;Open price;Orig. Open price;Size;Close price;Close type;Stop Loss price level;Profit Target price level;Balance;Slippage ($);Profit/Loss;Profit/Loss Pips;Comm/Swap;MAE ($);MAE (pips);MFE ($);MFE (pips);Drawdown;% Drawdown"

    # Row 1: Winning Trade
    row1 = "1001;EURUSD;buy;Strategy1;IS;;2023.01.01 12:00;2023.01.01 16:00;4.0;16;1.0500;1.0500;0.1;1.0550;ProfitTarget;1.0450;1.0550;10050.0;0.0;50.0;50.0;-2.0;-10.0;-10.0;60.0;60.0;0.0;0.0"

    # Row 2: Losing Trade
    row2 = "1002;EURUSD;sell;Strategy1;IS;;2023.01.02 10:00;2023.01.02 14:00;4.0;16;1.0600;1.0600;0.1;1.0650;StopLoss;1.0650;1.0500;10000.0;0.0;-50.0;-50.0;-2.0;-60.0;-60.0;10.0;10.0;50.0;0.5"

    content = f"{header}\n{row1}\n{row2}"
    return content


def test_import():
    """Test the import endpoint."""
    csv_content = create_dummy_csv()

    files = {"file": ("test_sqx.csv", csv_content, "text/csv")}

    data = {
        "strategy_name": "Test_SQX_Import",
        "symbol": "EURUSD",
        "timeframe": "H1",
        "initial_balance": 10000.0,
        "description": "Automated test import",
    }

    print(f"Sending request to {API_URL}...")
    try:
        response = requests.post(API_URL, files=files, data=data)

        if response.status_code == 200:
            print("SUCCESS: Import successful!")
            print(response.json())
        else:
            print(f"FAILURE: Status {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"ERROR: Could not connect to API. Is it running? {e}")


if __name__ == "__main__":
    test_import()
