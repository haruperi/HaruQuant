"""Routes for importing external backtest trades."""

import io
from datetime import datetime
from typing import Annotated, Any, List, Optional, Tuple

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.api.auth_utils import get_user_id_from_token
from services.execution.core import (
    BacktestResult,
    CloseType,
    EquityPoint,
    ExitReason,
    TradeRecord,
)
from services.utils.logger import logger
from backend.data.database.sqlite.database_operations import DatabaseManager

router = APIRouter()
db_manager = DatabaseManager()

# ... (Column constants retained) ...
# =========================================================================
# Strategy Quant X CSV Column Mapping
# =========================================================================
# Based on user request:
# "Ticket";"Symbol";"Type";"Result name";"Sample type";"Comment";
# "Open time";"Close time";"Time in trade";"BarsInTrade";
# "Open price";"Orig. Open price";"Size";"Close price";"Close type";
# "Stop Loss price level";"Profit Target price level";
# "Balance";"Slippage ($)";"Profit/Loss";"Profit/Loss Pips";"Comm/Swap";
# "MAE ($)";"MAE (pips)";"MFE ($)";"MFE (pips)";"Drawdown";"% Drawdown"

SQX_COL_TICKET = "Ticket"
SQX_COL_SYMBOL = "Symbol"
SQX_COL_TYPE = "Type"
SQX_COL_RESULT_NAME = "Result name"  # Strategy ID/Name within SQX
SQX_COL_SAMPLE_TYPE = "Sample type"  # IS/OOS
SQX_COL_COMMENT = "Comment"
SQX_COL_OPEN_TIME = "Open time"
SQX_COL_CLOSE_TIME = "Close time"
SQX_COL_TIME_IN_TRADE = "Time in trade"
SQX_COL_BARS_IN_TRADE = "BarsInTrade"
SQX_COL_OPEN_PRICE = "Open price"
SQX_COL_SIZE = "Size"
SQX_COL_CLOSE_PRICE = "Close price"
SQX_COL_CLOSE_TYPE = "Close type"
SQX_COL_SL_PRICE = "Stop Loss price level"
SQX_COL_TP_PRICE = "Profit Target price level"
SQX_COL_BALANCE = "Balance"
SQX_COL_SLIPPAGE = "Slippage ($)"
SQX_COL_PNL = "Profit/Loss"
SQX_COL_PNL_PIPS = "Profit/Loss Pips"
SQX_COL_COMM_SWAP = "Comm/Swap"
SQX_COL_MAE_USD = "MAE ($)"
SQX_COL_MAE_PIPS = "MAE (pips)"
SQX_COL_MFE_USD = "MFE ($)"
SQX_COL_MFE_PIPS = "MFE (pips)"
SQX_COL_DRAWDOWN = "Drawdown"
SQX_COL_DRAWDOWN_PCT = "% Drawdown"


def _parse_float(value: Any, default: float = 0.0) -> float:
    try:
        if pd.isna(value) or value == "":
            return default
        # Remove currency symbols if present? usually SQX exports raw numbers but good to be safe if string
        if isinstance(value, str):
            return float(value.replace("$", "").replace(",", "").strip())
        return float(value)
    except Exception:
        return default


def _parse_int(value: Any, default: int = 0) -> int:
    try:
        if pd.isna(value) or value == "":
            return default
        return int(float(value))  # Handle 1.0 cases
    except Exception:
        return default


def _parse_dt(value: Any) -> Optional[datetime]:
    if pd.isna(value) or value == "":
        return None
    # SQX format usually: "2023.01.01 12:00" or similar depending on locale
    # We'll try common pandas parsing
    try:
        # Cast to datetime explicitly for mypy
        return datetime.fromtimestamp(pd.to_datetime(value).timestamp())
    except Exception:
        return None


def _map_close_type(sqx_type: str) -> str:
    """Map SQX close types to internal canonical types."""
    # SQX Types example: "StopLoss", "ProfitTarget", "EndOfDay", "CloseOnTime"
    st = str(sqx_type).lower()
    if "stop" in st and "loss" in st:
        return CloseType.SL.value
    if "profit" in st or "target" in st:
        return CloseType.TP.value
    if "time" in st or "end" in st:
        return CloseType.TIME_EXIT.value
    return CloseType.SIGNAL_EXIT.value  # Default fallback


def _process_sqx_row(
    row: pd.Series,
    symbol_default: str,
    strategy_name_default: str,
    timeframe: str,
    initial_balance: float,
    idx: int,
) -> Tuple[TradeRecord, Optional[EquityPoint], float]:
    """Process a single SQX CSV row into TradeRecord and EquityPoint."""
    # 1. Parse Trade Record
    record = TradeRecord()

    # Identity
    record.ticket = _parse_int(row.get(SQX_COL_TICKET))
    record.symbol = str(row.get(SQX_COL_SYMBOL, symbol_default))
    record.type = str(row.get(SQX_COL_TYPE, "")).lower()  # "buy"/"sell"
    record.strategy_name = str(row.get(SQX_COL_RESULT_NAME, strategy_name_default))
    record.sample_type = str(row.get(SQX_COL_SAMPLE_TYPE, ""))
    record.comment = str(row.get(SQX_COL_COMMENT, ""))

    # Metadata passed from form
    record.signal_timeframe = timeframe
    record.execution_timeframe = timeframe  # Assumption

    # Timing
    record.open_time = _parse_dt(row.get(SQX_COL_OPEN_TIME))
    record.close_time = _parse_dt(row.get(SQX_COL_CLOSE_TIME))
    # SQX Time in trade is usually string or float days? Let's rely on calc if possible, or parse if needed.
    # If dates exist:
    if record.open_time and record.close_time:
        duration = record.close_time - record.open_time
        record.time_in_trade = duration.total_seconds() / 3600.0  # Hours
    record.bars_in_trade = _parse_int(row.get(SQX_COL_BARS_IN_TRADE))

    # Entry/Exit
    record.open_price = _parse_float(row.get(SQX_COL_OPEN_PRICE))
    record.size = _parse_float(row.get(SQX_COL_SIZE))
    record.close_price = _parse_float(row.get(SQX_COL_CLOSE_PRICE))

    sqx_close_type = str(row.get(SQX_COL_CLOSE_TYPE, ""))
    record.close_type = _map_close_type(sqx_close_type)
    record.exit_reason = ExitReason.STRATEGY_EXIT.value  # Defaut

    record.stop_loss_price_level = _parse_float(row.get(SQX_COL_SL_PRICE))
    record.profit_target_price_level = _parse_float(row.get(SQX_COL_TP_PRICE))

    # Financials
    record.profit_loss = _parse_float(row.get(SQX_COL_PNL))
    record.profit_loss_pips = _parse_float(row.get(SQX_COL_PNL_PIPS))
    record.commission = _parse_float(
        row.get(SQX_COL_COMM_SWAP)
    )  # SQX often bundles comm/swap
    record.slippage_usd = _parse_float(row.get(SQX_COL_SLIPPAGE))

    # Metrics
    record.mae_usd = _parse_float(row.get(SQX_COL_MAE_USD))
    record.mae_pips = _parse_float(row.get(SQX_COL_MAE_PIPS))
    record.mfe_usd = _parse_float(row.get(SQX_COL_MFE_USD))
    record.mfe_pips = _parse_float(row.get(SQX_COL_MFE_PIPS))
    record.drawdown = _parse_float(row.get(SQX_COL_DRAWDOWN))

    # State at trade
    balance_after = _parse_float(row.get(SQX_COL_BALANCE))
    if idx == 0 and balance_after == 0:
        # If SQX didn't export balance, we simulate it
        balance_after = initial_balance + record.profit_loss

    # NOTE: SQX 'Balance' is usually post-trade.
    # We want 'balance_at_entry' for the record?
    # Approximate: Balance After - PnL = Pre-trade Balance (roughly)
    record.balance_at_entry = balance_after - record.profit_loss

    # 2. Build Equity Point
    ep = None
    if record.close_time:
        dd = _parse_float(row.get(SQX_COL_DRAWDOWN))
        dd_pct = _parse_float(row.get(SQX_COL_DRAWDOWN_PCT))
        if pd.isna(dd_pct) and balance_after > 0:
            # Approximated if missing
            dd_pct = (dd / balance_after) * 100 if dd > 0 else 0

        ep = EquityPoint(
            timestamp=record.close_time,
            balance=balance_after,
            equity=balance_after,  # Assumption since trade is closed
            drawdown=dd,
            drawdown_percent=dd_pct,
        )

    return record, ep, balance_after


@router.post("/sqx", summary="Import Strategy Quant X Trades")
async def import_sqx_trades(
    file: Annotated[UploadFile, File(...)],
    strategy_name: Annotated[str, Form(...)],
    symbol: Annotated[str, Form(...)],
    timeframe: Annotated[str, Form(...)],
    user_id: Annotated[int, Depends(get_user_id_from_token)],
    alias: Annotated[Optional[str], Form()] = None,
    description: Annotated[Optional[str], Form()] = None,
    initial_balance: Annotated[float, Form()] = 10000.0,
):
    """
    Import trades from a Strategy Quant X CSV export.

    Creates a new Backtest Run and saves the trades/equity curve.
    """
    try:
        content = await file.read()
        # Decode - SQX often exports in UTF-8 or CP1252. Try utf-8 first.
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("cp1252")

        # Determine delimiter - SQX is usually ";" for CSV exports
        delimiter = ";" if ";" in text[:100] else ","

        df = pd.read_csv(io.StringIO(text), sep=delimiter)

        # Verify columns
        required = [
            SQX_COL_TICKET,
            SQX_COL_SYMBOL,
            SQX_COL_OPEN_TIME,
            SQX_COL_CLOSE_TIME,
            SQX_COL_PNL,
        ]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns in CSV: {', '.join(missing)}",
            )

        trades: List[TradeRecord] = []
        equity_curve: List[EquityPoint] = []

        # Process rows
        for idx, row in df.iterrows():
            record, ep, _ = _process_sqx_row(
                row, symbol, strategy_name, timeframe, initial_balance, idx
            )
            trades.append(record)
            if ep:
                equity_curve.append(ep)

        # Sort trades by close time just in case
        trades.sort(key=lambda x: x.close_time or datetime.min)
        equity_curve.sort(key=lambda x: x.timestamp)

        final_balance = equity_curve[-1].balance if equity_curve else initial_balance
        final_equity = equity_curve[-1].equity if equity_curve else initial_balance

        # Construct BacktestResult
        # We need start/end dates
        start_date = (
            trades[0].open_time if trades and trades[0].open_time else datetime.now()
        )
        end_date = (
            trades[-1].close_time
            if trades and trades[-1].close_time
            else datetime.now()
        )

        result = BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance,
            backtest_mode="import_sqx",
            data_step_mode="unknown",
            final_balance=final_balance,
            final_equity=final_equity,
            trades=trades,
            equity_curve=equity_curve,
            metadata={
                "alias": alias,
                "description": description
                or f"Imported from Strategy Quant X CSV: {file.filename}",
                "source": "strategy_quant_x",
                "import_date": str(datetime.now()),
            },
        )

        # Save to DB
        backtest_id = db_manager.save_backtest_result(
            result, alias=alias, description=description, user_id=user_id
        )

        return {
            "status": "success",
            "backtest_id": backtest_id,
            "message": f"Successfully imported {len(trades)} trades.",
            "trades_count": len(trades),
        }

    except Exception as e:
        logger.error(f"SQX Import failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

