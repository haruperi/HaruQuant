"""Trade routes for retrieving individual trade details and chart data."""

import sqlite3
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, status

from apps.logger import logger
from apps.mt5.data import MT5Data, TimeFrame
from apps.sqlite.database_operations import DatabaseManager

router = APIRouter()
db_manager = DatabaseManager()
mt5_data = MT5Data()


def _get_backtest_info(backtest_id: int) -> Dict[str, Any]:
    conn = sqlite3.connect(db_manager.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    backtest_query = """
    SELECT backtest_id, symbols, timeframes, start_date, end_date
    FROM backtest_runs
    WHERE backtest_id = ?
    """
    cursor.execute(backtest_query, (backtest_id,))
    backtest_row = cursor.fetchone()
    conn.close()

    if not backtest_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backtest with ID {backtest_id} not found",
        )

    return dict(backtest_row)


def _parse_json_field(value):
    if isinstance(value, str):
        import json

        return json.loads(value)
    return value


def _resolve_symbol_timeframe(
    trade_data: Dict[str, Any], backtest_info: Dict[str, Any]
):
    symbols = _parse_json_field(backtest_info["symbols"])
    timeframes = _parse_json_field(backtest_info["timeframes"])

    symbol = trade_data.get("symbol") or (symbols[0] if symbols else None)
    timeframe_str = (
        trade_data.get("signal_timeframe")
        or trade_data.get("execution_timeframe")
        or (timeframes[0] if timeframes else "H1")
    )

    return symbol, timeframe_str


def _parse_backtest_dates(backtest_info: Dict[str, Any]):
    start_date = (
        datetime.fromisoformat(backtest_info["start_date"])
        if backtest_info["start_date"]
        else None
    )
    end_date = (
        datetime.fromisoformat(backtest_info["end_date"])
        if backtest_info["end_date"]
        else None
    )

    if not start_date or not end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Backtest start_date and end_date are required",
        )

    return start_date, end_date


def _fetch_all_trades(backtest_id: int):
    conn = sqlite3.connect(db_manager.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    trades_query = """
    SELECT *
    FROM backtest_trades
    WHERE backtest_id = ?
    ORDER BY
        CASE
            WHEN close_time IS NOT NULL THEN close_time
            ELSE open_time
        END ASC
    """
    cursor.execute(trades_query, (backtest_id,))
    trades_rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in trades_rows]


def _load_chart_bars(
    symbol: str, timeframe: TimeFrame, start_date, end_date, timeframe_str: str
):
    cache_key = f"chart_{symbol}_{timeframe_str}_{start_date.isoformat()}_{end_date.isoformat()}"
    cached_data = mt5_data.get_cached(cache_key)
    if cached_data:
        logger.info(f"Using cached chart data for {symbol} {timeframe_str}")
        return cached_data

    bars = mt5_data.get_bars(
        symbol=symbol,
        timeframe=timeframe,
        start=start_date,
        end=end_date,
        as_dataframe=False,
    )

    if not bars:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Failed to fetch chart data for {symbol}. "
                "MT5 may be unavailable or symbol not found."
            ),
        )

    mt5_data.cache(cache_key, bars, ttl=3600)
    logger.info(f"Cached chart data for {symbol} {timeframe_str}: {len(bars)} bars")
    return bars


def _to_timestamp(bar_time) -> int:
    if isinstance(bar_time, datetime):
        return int(bar_time.timestamp())
    if isinstance(bar_time, (int, float)):
        return int(bar_time)
    try:
        return int(bar_time)
    except (ValueError, TypeError):
        return int(datetime.fromisoformat(str(bar_time)).timestamp())


def _build_chart_data(bars):
    chart_data = []
    for bar in bars:
        if isinstance(bar, dict):
            bar_time = bar["time"]
            open_price = float(bar["open"])
            high_price = float(bar["high"])
            low_price = float(bar["low"])
            close_price = float(bar["close"])
            volume = int(bar.get("tick_volume", 0))
        else:
            bar_time = bar[0]
            open_price = float(bar[1])
            high_price = float(bar[2])
            low_price = float(bar[3])
            close_price = float(bar[4])
            volume = int(bar[5] if len(bar) > 5 else 0)

        chart_data.append(
            {
                "time": _to_timestamp(bar_time),
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume,
            }
        )
    return chart_data


@router.get("/{trade_id}")
async def get_trade_by_id(trade_id: int) -> Dict[str, Any]:
    """
    Get single trade details by trade_id.

    Joins backtest_trades with backtest_runs to include backtest metadata.

    Args:
        trade_id: The unique ID of the trade

    Returns:
        Dictionary containing all trade fields plus backtest metadata

    Raises:
        HTTPException: 404 if trade not found, 500 for server errors
    """
    try:
        logger.info(f"Fetching trade {trade_id} from database: {db_manager.db_path}")
        conn = sqlite3.connect(db_manager.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Query joining backtest_trades and backtest_runs
        query = """
        SELECT
            t.*,
            br.symbols as backtest_symbols,
            br.timeframes as backtest_timeframes,
            br.start_date,
            br.end_date,
            br.strategy_name as backtest_strategy_name,
            br.initial_balance
        FROM backtest_trades t
        JOIN backtest_runs br ON t.backtest_id = br.backtest_id
        WHERE t.trade_id = ?
        """

        cursor.execute(query, (trade_id,))
        row = cursor.fetchone()

        logger.info(
            f"Query executed for trade {trade_id}, row found: {row is not None}"
        )

        if not row:
            # Log what trades exist for debugging
            cursor.execute("SELECT COUNT(*) FROM backtest_trades")
            total_trades = cursor.fetchone()[0]
            logger.warning(
                f"Trade {trade_id} not found. Total trades in DB: {total_trades}"
            )

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade with ID {trade_id} not found",
            )

        # Convert Row to dict
        trade_data = dict(row)

        conn.close()

        logger.info(
            f"Retrieved trade {trade_id} from backtest {trade_data.get('backtest_id')}"
        )
        return trade_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving trade {trade_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve trade: {str(e)}",
        )


@router.get("/{trade_id}/backtest-chart-data")
async def get_trade_chart_data(
    trade_id: int, bars_before: int = 25, bars_after: int = 25
) -> Dict[str, Any]:
    """
    Get OHLCV chart data for the entire backtest period containing this trade.

    This endpoint fetches the full backtest dataset once and returns it along with
    all trades, allowing the frontend to keep data in memory and handle navigation
    client-side.

    Args:
        trade_id: The unique ID of the trade
        bars_before: Number of bars to show before trade entry (used for initial window calculation)
        bars_after: Number of bars to show after trade exit (used for initial window calculation)

    Returns:
        Dictionary containing:
            - chart_data: Full OHLCV dataset for entire backtest period
            - symbol: Trading symbol
            - timeframe: Chart timeframe
            - all_trades: List of all trades in this backtest (sorted by close_time)
            - current_trade_index: Index of current trade in the list
            - bars_before: Initial context before trade
            - bars_after: Initial context after trade

    Raises:
        HTTPException: 404 if trade not found, 503 if MT5 unavailable, 500 for other errors
    """
    try:
        # First, get the trade to find its backtest_id
        trade_data = await get_trade_by_id(trade_id)
        backtest_id = trade_data["backtest_id"]

        backtest_info = _get_backtest_info(backtest_id)
        symbol, timeframe_str = _resolve_symbol_timeframe(trade_data, backtest_info)

        if not symbol:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to determine trading symbol for chart data",
            )

        # Convert timeframe string to TimeFrame enum
        try:
            timeframe = TimeFrame.from_string(timeframe_str)
        except ValueError:
            logger.warning(f"Invalid timeframe '{timeframe_str}', defaulting to H1")
            timeframe = TimeFrame.H1
            timeframe_str = "H1"

        start_date, end_date = _parse_backtest_dates(backtest_info)
        all_trades = _fetch_all_trades(backtest_id)

        # Find current trade index in the sorted list
        current_trade_index = next(
            (i for i, t in enumerate(all_trades) if t["trade_id"] == trade_id), 0
        )

        # Fetch OHLCV data from MT5 for entire backtest period
        logger.info(
            f"Fetching chart data for {symbol} {timeframe_str} from {start_date} to {end_date}"
        )

        bars = _load_chart_bars(symbol, timeframe, start_date, end_date, timeframe_str)
        chart_data = _build_chart_data(bars)

        logger.info(
            f"Successfully prepared {len(chart_data)} bars for trade {trade_id}, "
            f"backtest {backtest_id}, symbol {symbol}"
        )

        return {
            "chart_data": chart_data,
            "symbol": symbol,
            "timeframe": timeframe_str,
            "all_trades": all_trades,
            "current_trade_index": current_trade_index,
            "bars_before": bars_before,
            "bars_after": bars_after,
            "total_bars": len(chart_data),
            "backtest_start": start_date.isoformat(),
            "backtest_end": end_date.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error retrieving chart data for trade {trade_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chart data: {str(e)}",
        )
