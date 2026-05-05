"""Dukascopy data provider for historical market data."""

import json
import random
import string
from datetime import datetime, timedelta
from time import sleep
from typing import Optional, Tuple

import pandas as pd
import requests

from haruquant.utils import logger
from haruquant.data import get_instrument

TIME_UNIT_MONTH = "MONTH"
TIME_UNIT_WEEK = "WEEK"
TIME_UNIT_DAY = "DAY"
TIME_UNIT_HOUR = "HOUR"
TIME_UNIT_MIN = "MIN"
TIME_UNIT_SEC = "SEC"
TIME_UNIT_TICK = "TICK"

INTERVAL_MONTH_1 = f"1{TIME_UNIT_MONTH}"
INTERVAL_WEEK_1 = f"1{TIME_UNIT_WEEK}"
INTERVAL_DAY_1 = f"1{TIME_UNIT_DAY}"
INTERVAL_HOUR_4 = f"4{TIME_UNIT_HOUR}"
INTERVAL_HOUR_1 = f"1{TIME_UNIT_HOUR}"
INTERVAL_MIN_30 = f"30{TIME_UNIT_MIN}"
INTERVAL_MIN_15 = f"15{TIME_UNIT_MIN}"
INTERVAL_MIN_10 = f"10{TIME_UNIT_MIN}"
INTERVAL_MIN_5 = f"5{TIME_UNIT_MIN}"
INTERVAL_MIN_1 = f"1{TIME_UNIT_MIN}"
INTERVAL_SEC_30 = f"30{TIME_UNIT_SEC}"
INTERVAL_SEC_10 = f"10{TIME_UNIT_SEC}"
INTERVAL_SEC_1 = f"1{TIME_UNIT_SEC}"
INTERVAL_TICK = TIME_UNIT_TICK

_interval_units = {
    INTERVAL_MONTH_1: TIME_UNIT_MONTH,
    INTERVAL_WEEK_1: TIME_UNIT_WEEK,
    INTERVAL_DAY_1: TIME_UNIT_DAY,
    INTERVAL_HOUR_4: TIME_UNIT_HOUR,
    INTERVAL_HOUR_1: TIME_UNIT_HOUR,
    INTERVAL_MIN_30: TIME_UNIT_MIN,
    INTERVAL_MIN_15: TIME_UNIT_MIN,
    INTERVAL_MIN_10: TIME_UNIT_MIN,
    INTERVAL_MIN_5: TIME_UNIT_MIN,
    INTERVAL_MIN_1: TIME_UNIT_MIN,
    INTERVAL_SEC_30: TIME_UNIT_SEC,
    INTERVAL_SEC_10: TIME_UNIT_SEC,
    INTERVAL_SEC_1: TIME_UNIT_SEC,
    INTERVAL_TICK: TIME_UNIT_TICK,
}

OFFER_SIDE_BID = "B"
OFFER_SIDE_ASK = "A"


def _resample_to_nearest(
    timestamp: datetime,
    time_unit: str,
    interval_value: int,
) -> datetime:
    # Round to the nearest time unit based on the interval value
    if time_unit == TIME_UNIT_SEC:
        subtraction = timestamp.second % interval_value
        return timestamp - timedelta(
            seconds=subtraction,
            microseconds=timestamp.microsecond,
        )
    elif time_unit == TIME_UNIT_MIN:
        subtraction = timestamp.minute % interval_value
        return timestamp - timedelta(
            minutes=subtraction,
            seconds=timestamp.second,
            microseconds=timestamp.microsecond,
        )
    elif time_unit == TIME_UNIT_HOUR:
        subtraction = timestamp.hour % interval_value
        return timestamp - timedelta(
            hours=subtraction,
            minutes=timestamp.minute,
            seconds=timestamp.second,
            microseconds=timestamp.microsecond,
        )
    elif time_unit == TIME_UNIT_DAY:
        subtraction = timestamp.day % interval_value
        return timestamp - timedelta(
            days=subtraction,
            hours=timestamp.hour,
            minutes=timestamp.minute,
            seconds=timestamp.second,
            microseconds=timestamp.microsecond,
        )
    elif time_unit == TIME_UNIT_WEEK:
        subtraction = (timestamp.weekday() + 1) % (interval_value * 7)
        return timestamp - timedelta(
            days=subtraction,
            hours=timestamp.hour,
            minutes=timestamp.minute,
            seconds=timestamp.second,
            microseconds=timestamp.microsecond,
        )
    elif time_unit == TIME_UNIT_MONTH:
        month = (timestamp.month // interval_value) + 1
        return datetime(timestamp.year, month, 1, 0, 0, 0, 0, timestamp.tzinfo)
    elif time_unit == TIME_UNIT_TICK:
        return timestamp

    raise NotImplementedError(f"resampling not implemented for {time_unit}")


def _get_dataframe_columns_for_timeunit(time_unit: str) -> list[str]:

    ohlc_df = ["timestamp", "open", "high", "low", "close", "volume"]
    tick_df = ["timestamp", "bidprice", "askprice", "bidvolume", "askvolume"]

    df = {
        TIME_UNIT_DAY: ohlc_df,
        TIME_UNIT_HOUR: ohlc_df,
        TIME_UNIT_MIN: ohlc_df,
        TIME_UNIT_MONTH: ohlc_df,
        TIME_UNIT_SEC: ohlc_df,
        TIME_UNIT_TICK: tick_df,
        TIME_UNIT_WEEK: ohlc_df,
    }[time_unit]

    return df


def _fetch(
    instrument: str,
    interval: str,
    offer_side: str,
    last_update: int,
    limit: Optional[int] = None,
):
    characters = string.ascii_letters + string.digits
    jsonp = f"_callbacks____{''.join(random.choices(characters, k=9))}"

    query_params = {
        "path": "chart/json3",
        "splits": "true",
        "stocks": "true",
        "time_direction": "N",
        "jsonp": jsonp,
        "last_update": f"{int(last_update)}",
        "offer_side": f"{offer_side}",
        "instrument": f"{instrument}",
        "interval": f"{interval}",
    }

    if limit is not None:
        # max limit is 30_000
        query_params["limit"] = f"{int(limit)}"

    base_url = "https://freeserv.dukascopy.com/2.0/index.php"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
        "Host": "freeserv.dukascopy.com",
        "Referer": "https://freeserv.dukascopy.com/2.0/?path=chart/index&showUI=true&showTabs=true&showParameterToolbar=true&showOfferSide=true&allowInstrumentChange=true&allowPeriodChange=true&allowOfferSideChange=true&showAdditionalToolbar=true&showExportImportWorkspace=true&allowSocialSharing=true&showUndoRedoButtons=true&showDetachButton=true&presentationType=candle&axisX=true&axisY=true&legend=true&timeline=true&showDateSeparators=true&showZoom=true&showScrollButtons=true&showAutoShiftButton=true&crosshair=true&borders=false&freeMode=false&theme=Pastelle&uiColor=%23000&availableInstruments=l%3A&instrument=EUR/USD&period=5&offerSide=BID&timezone=0&live=true&allowPan=true&width=100%25&height=700&adv=popup&lang=en",
    }

    # Timeout set to 60 seconds to prevent hanging requests
    response = requests.get(base_url, headers=headers, params=query_params, timeout=60)

    jsonText = response.text.removeprefix(f"{jsonp}(").removesuffix(");")

    return json.loads(jsonText)


def _process_stream_row(
    row: list, interval: str, end_timestamp: Optional[int]
) -> Optional[list]:
    """
    Process a single row from stream data.

    Args:
        row: Data row
        interval: Data interval
        end_timestamp: End timestamp for filtering

    Returns:
        Processed row or None if past end timestamp
    """
    if row is None:
        return None

    if end_timestamp is not None and row[0] > end_timestamp:
        return None

    if interval == INTERVAL_TICK:
        row[-1] = row[-1] / 1_000_000
        row[-2] = row[-2] / 1_000_000

    return row


def _handle_stream_error(
    e: Exception, no_of_retries: int, max_retries: Optional[int]
) -> bool:
    """
    Handle stream error and determine if should retry.

    Args:
        e: Exception that occurred
        no_of_retries: Current retry count
        max_retries: Maximum retries allowed

    Returns:
        True if should continue, False if should raise
    """
    import traceback

    stacktrace = traceback.format_exc()
    no_of_retries += 1

    if max_retries is not None and (no_of_retries - 1) > max_retries:
        logger.error("error fetching")
        logger.error(f"Exception: {e}")
        logger.error(stacktrace)
        raise e
    else:
        logger.error(f"an error occured: {e}")
        logger.error(f"Stacktrace: {stacktrace}")
        logger.error("retrying")
        sleep(1)
    return True


def _process_stream_batch(
    lastUpdates: list,
    is_first_iteration: bool,
    cursor: int,
    interval: str,
    end_timestamp: Optional[int],
) -> Tuple[list, int]:
    """
    Process a batch of stream updates.

    Args:
        lastUpdates: List of updates from fetch
        is_first_iteration: Whether this is the first iteration
        cursor: Current cursor position
        interval: Data interval
        end_timestamp: End timestamp for filtering

    Returns:
        Tuple of (processed rows, new cursor)
    """
    if not is_first_iteration and lastUpdates[0][0] == cursor:
        lastUpdates = lastUpdates[1:]

    processed_rows: list[list] = []
    for row in lastUpdates:
        processed_row = _process_stream_row(row, interval, end_timestamp)
        if processed_row is None:
            return processed_rows, cursor
        processed_rows.append(processed_row)
        cursor = row[0]

    return processed_rows, cursor


def _should_continue_streaming(lastUpdates: list, end: Optional[datetime]) -> bool:
    """Check if streaming should continue after empty result."""
    if len(lastUpdates) < 1:
        return end is None
    return True


def _stream(
    instrument: str,
    interval: str,
    offer_side: str,
    start: datetime,
    end: Optional[datetime] = None,
    max_retries: int = 7,
    limit: Optional[int] = None,
):
    no_of_retries = 0
    cursor = int(start.timestamp() * 1000)
    end_timestamp = None
    if end is not None:
        end_timestamp = int(end.timestamp() * 1000)

    is_first_iteration = True

    logger.info(f"Start Date :{start.isoformat()}")
    logger.info(f"End Date :{'' if end is None else end.isoformat()}")

    while True:
        try:
            lastUpdates = _fetch(
                instrument=instrument,
                interval=interval,
                offer_side=offer_side,
                last_update=cursor,
                limit=limit,
            )

            if not _should_continue_streaming(lastUpdates, end):
                break

            processed_rows, cursor = _process_stream_batch(
                lastUpdates, is_first_iteration, cursor, interval, end_timestamp
            )

            yield from processed_rows

            if len(processed_rows) == 0:
                return

            logger.success(
                f"current timestamp :{datetime.fromtimestamp(cursor / 1000).isoformat()}"
            )

            no_of_retries = 0
            is_first_iteration = False

        except Exception as e:
            if not _handle_stream_error(e, no_of_retries, max_retries):
                return
            no_of_retries += 1
            continue


def fetch(
    instrument: str,
    interval: str,
    offer_side: str,
    start: datetime,
    end: datetime,
    max_retries: int = 7,
    limit: int = 30_000,  # max 30_000
):
    """Fetch historical data from Dukascopy."""
    instrument = get_instrument(instrument)
    time_unit = _interval_units[interval]
    columns = _get_dataframe_columns_for_timeunit(time_unit)

    data = []

    datafeed = _stream(
        instrument=instrument,
        interval=interval,
        offer_side=offer_side,
        start=start,
        end=end,
        max_retries=max_retries,
        limit=limit,
    )

    for row in datafeed:
        data.append(row)

    df = pd.DataFrame(data=data, columns=columns)
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms",
        utc=True,
    )
    df = df.set_index("timestamp")
    return df


def live_fetch(
    instrument: str,
    interval_value: int,
    time_unit: str,
    offer_side: str,
    start: datetime,
    end: datetime,
    max_retries: int = 7,
    limit: int = 30_000,  # max 30_000
):
    """Fetch live historical data from Dukascopy."""
    instrument = get_instrument(instrument)
    assert interval_value > 0

    # validate time unit
    _resample_to_nearest(
        datetime.now(),
        time_unit,
        interval_value,
    )

    open, high, low, close, volume = None, 0, 0, 0, 0

    price_index = {
        OFFER_SIDE_BID: 1,
        OFFER_SIDE_ASK: 2,
    }[offer_side]

    volume_index = {
        OFFER_SIDE_BID: -2,
        OFFER_SIDE_ASK: -1,
    }[offer_side]

    last_timestamp = None

    columns = _get_dataframe_columns_for_timeunit(time_unit)
    df = pd.DataFrame(columns=columns)
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        unit="ms",
        utc=True,
    )
    df = df.set_index("timestamp")

    datafeed = _stream(
        instrument=instrument,
        interval=INTERVAL_TICK,
        offer_side=offer_side,
        start=start,
        end=end,
        max_retries=max_retries,
        limit=limit,
    )

    yield df

    last_tick_count = 0

    for tick_count, row in enumerate(datafeed, 0):

        timestamp = _resample_to_nearest(
            pd.to_datetime(
                row[0],
                unit="ms",
                utc=True,
            ),
            time_unit,
            interval_value,
        )

        if last_timestamp is None:
            last_timestamp = timestamp

        if time_unit == TIME_UNIT_TICK and interval_value == 1:
            new_row = pd.DataFrame([row[1:]], index=[timestamp], columns=df.columns)
            df = pd.concat([df, new_row])
            yield df
            continue

        new_tick_count = tick_count // interval_value

        if (
            time_unit != TIME_UNIT_TICK
            and timestamp.timestamp() != last_timestamp.timestamp()
        ) or (time_unit == TIME_UNIT_TICK and last_tick_count != new_tick_count):
            if open is not None:
                new_row = pd.DataFrame(
                    [[open, high, low, close, volume]],
                    index=[last_timestamp],
                    columns=df.columns,
                )
                df = pd.concat([df, new_row])

                yield df
            last_timestamp = timestamp
            last_tick_count = new_tick_count
            open = None

        if open is None:
            open = row[price_index]
            close = open
            low = open
            high = open
            volume = 0

        close = row[price_index]
        high = max(high, close)
        low = min(low, close)
        volume += row[volume_index]

        # Update the row at timestamp if it exists, otherwise it will be added in the next iteration
        if timestamp in df.index:
            df.loc[timestamp, :] = [open, high, low, close, volume]
        else:
            new_row = pd.DataFrame(
                [[open, high, low, close, volume]],
                index=[timestamp],
                columns=df.columns,
            )
            df = pd.concat([df, new_row])

        yield df

