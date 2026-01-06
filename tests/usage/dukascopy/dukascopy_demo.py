"""Dukascopy demo examples."""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to Python path to allow imports
# File is at examples/mt5/dukascopy_demo.py, so go up 3 levels to project root
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


from apps.dukascopy import INTERVAL_HOUR_1, OFFER_SIDE_BID, fetch, live_fetch, TIME_UNIT_HOUR  # noqa: E402

def example01_fetch_historical_data():

    df = fetch(
        instrument="GBPUSD",
        interval=INTERVAL_HOUR_1,
        offer_side=OFFER_SIDE_BID,
        start=datetime(2025, 1, 1),
        end=datetime(2025, 12, 1),
    )
    print(df)

def example02_fetch_live_with_end_data():
    now = datetime.now()
    start = datetime(now.year, now.month, now.day)
    end = start + timedelta(hours=24)
    instrument = "GBPUSD"
    offer_side = OFFER_SIDE_BID

    iterator = live_fetch(
        instrument,
        1,
        TIME_UNIT_HOUR,
        offer_side,
        start,
        end,
    )

    for df in iterator:
        pass

    print(df)


def example03_fetch_live_with_none_end():
    now = datetime.now()
    start = datetime(now.year, now.month, now.day)
    end = None
    instrument = "GBPUSD"
    offer_side = OFFER_SIDE_BID

    df_iterator = live_fetch(
        instrument,
        1,
        TIME_UNIT_HOUR,
        offer_side,
        start,
        end,
    )

    for df in df_iterator:
        # Do something with latest data
        pass




    

if __name__ == "__main__":
    example01_fetch_historical_data()
    #example02_fetch_live_with_end_data()
    #example03_fetch_live_with_none_end()
    
