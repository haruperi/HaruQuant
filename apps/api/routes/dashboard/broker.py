"""Broker routes."""

import json
from datetime import datetime, timedelta
from typing import Annotated, Any, Dict, Optional, Union, cast

from fastapi import APIRouter, Header

from apps.api.auth_utils import verify_token
from apps.api.models import (
    DashboardActiveStrategyItem,
    BrokerStatusResponse,
    DashboardDailyPnlPoint,
    DashboardEquityCurveResponse,
    DashboardEquityPoint,
    DashboardSummaryResponse,
)
from apps.utils.logger import logger
from apps.mt5.client import MT5Client
from apps.sqlite.database_operations import DatabaseManager

router = APIRouter()
db_manager = DatabaseManager()

# Global client instance
client = MT5Client()
_last_login: Optional[int] = None
_last_server: Optional[str] = None
_last_password: Optional[str] = None
_last_path: Optional[str] = None


def get_last_credentials() -> Dict[str, Any]:
    """Get last known MT5 credentials for auto-reconnect."""
    return {
        "login": _last_login,
        "server": _last_server,
        "password": _last_password,
        "path": _last_path,
    }


def _parse_credentials(credentials: Union[str, Dict[str, Any], None]) -> Dict[str, Any]:
    """Parse broker credentials from various formats."""
    if not credentials:
        return {}

    if isinstance(credentials, dict):
        return credentials

    if isinstance(credentials, str):
        try:
            return cast(Dict[str, Any], json.loads(credentials))
        except json.JSONDecodeError:
            logger.error("Failed to parse broker credentials JSON")
            return {}

    return {}


def _update_mt5_connection(user_id: int) -> None:
    """Update and reconnect MT5 client if user credentials differ."""
    global client
    global _last_login, _last_server, _last_password, _last_path
    try:
        # Use the helper method which handles the nested accounts list logic correctly
        creds = db_manager.get_mt5_credentials(user_id) or {}

        login = creds.get("login")
        password = creds.get("password")
        server = creds.get("server")
        path = creds.get("path", "")

        # Check if we have valid credentials to use
        if login and password and server:
            # Convert login to int if string
            try:
                login_int = int(login)
            except (ValueError, TypeError):
                login_int = 0

            # Update Client if credentials changed or not connected
            credentials_changed = (_last_login != login_int) or (_last_server != server)

            if credentials_changed or not client.is_connected():
                if credentials_changed:
                    logger.info(f"Updating MT5 client credentials for user {user_id}")
                    _last_login = login_int
                    _last_server = server
                    _last_password = password
                    _last_path = path
                    # Note: Don't call client.shutdown() here - it disconnects the global client
                    # and breaks other endpoints that rely on the connection.
                    # The connect() method will handle reconnection properly.

                logger.info("Connecting to MT5...")
                client.connect(
                    path=path,
                    login=login_int,
                    password=password,
                    server=server,
                )

    except Exception as e:
        logger.error(f"Error fetching/applying user settings: {e}")


def _coerce_deal_value(deal: Any, attr_name: str, default: Any = None) -> Any:
    """Return deal attribute value from MT5 namedtuple-like rows."""
    return getattr(deal, attr_name, default)


def _get_authenticated_user_id(authorization: Optional[str]) -> Optional[int]:
    """Resolve authenticated user id from Bearer header."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        return verify_token(token, db_manager)
    return None


@router.get("/broker", response_model=BrokerStatusResponse)
async def get_broker_status(authorization: Annotated[Optional[str], Header()] = None):
    """
    Get current broker connection status and account info.

    Authenticated endpoint:
    1. Verifies user token.
    2. Fetches user settings (broker credentials).
    3. Initializes MT5 connection with those credentials if needed.
    """
    global client

    # 1. Authenticate User
    user_id = _get_authenticated_user_id(authorization)

    # If not authenticated, we can return disconnected or attempt default/global connection
    # But for invalid "login" error fix, we really need the user's credentials.
    # We will proceed if we have a user_id to try and connect.

    if user_id:
        _update_mt5_connection(user_id)

    # 4. Return Status
    try:
        if not client.is_connected() and _last_login and _last_server:
            # Last ditch attempt to initialize if it was already configured but dropped
            creds = db_manager.get_mt5_credentials(user_id) or {}
            client.connect(
                path=creds.get("path", ""),
                login=_last_login,
                password=creds.get("password", ""),
                server=_last_server,
            )

        if not client.is_connected():
            return BrokerStatusResponse(
                status="Disconnected",
                broker_name="None",
                equity=0.0,
                balance=0.0,
                margin_level=0.0,
                free_margin=0.0,
            )

        account = client.account_info()
        if account is None:
            return BrokerStatusResponse(
                status="Connected",
                broker_name=_last_server or "Unknown",
                equity=0.0,
                balance=0.0,
                margin_level=0.0,
                free_margin=0.0,
            )

        return BrokerStatusResponse(
            status="Connected",
            broker_name=_last_server or "Unknown Broker",
            equity=float(getattr(account, "equity", 0.0) or 0.0),
            balance=float(getattr(account, "balance", 0.0) or 0.0),
            margin_level=float(getattr(account, "margin_level", 0.0) or 0.0),
            free_margin=float(getattr(account, "margin_free", 0.0) or 0.0),
        )

    except Exception as e:
        logger.error(f"Error getting broker status: {e}")
        return BrokerStatusResponse(
            status="Error",
            broker_name="Connection Error",
            equity=0.0,
            balance=0.0,
            margin_level=0.0,
            free_margin=0.0,
        )


@router.get("/equity-curve", response_model=DashboardEquityCurveResponse)
async def get_equity_curve(authorization: Annotated[Optional[str], Header()] = None):
    """
    Build dashboard equity curve from MT5 historical deals.

    Uses the authenticated user's MT5 credentials and current account balance to
    back-calculate the starting balance across the available deal history.
    """
    global client

    user_id = _get_authenticated_user_id(authorization)

    if user_id:
        _update_mt5_connection(user_id)

    if not client.is_connected():
        return DashboardEquityCurveResponse(points=[], history_span_seconds=0.0, point_count=0)

    try:
        deals = client.history_deals_get(datetime(2000, 1, 1), datetime.now())
        if deals is None:
            deals = []

        sorted_deals = sorted(
            list(deals),
            key=lambda row: int(_coerce_deal_value(row, "time_msc", 0) or 0)
            or int(_coerce_deal_value(row, "time", 0) or 0),
        )

        account = client.account_info()
        current_balance = float(getattr(account, "balance", 0.0) or 0.0) if account else 0.0

        running_net = 0.0
        total_net = 0.0
        normalized_rows = []

        for deal in sorted_deals:
            deal_time = int(_coerce_deal_value(deal, "time", 0) or 0)
            if deal_time <= 0:
                continue

            profit = float(_coerce_deal_value(deal, "profit", 0.0) or 0.0)
            commission = float(_coerce_deal_value(deal, "commission", 0.0) or 0.0)
            swap = float(_coerce_deal_value(deal, "swap", 0.0) or 0.0)
            net = profit + commission + swap
            total_net += net
            normalized_rows.append((deal_time, net))

        if not normalized_rows:
            return DashboardEquityCurveResponse(points=[], history_span_seconds=0.0, point_count=0)

        starting_balance = current_balance - total_net
        points = []

        first_timestamp = normalized_rows[0][0]
        points.append(
            DashboardEquityPoint(
                timestamp=datetime.fromtimestamp(first_timestamp).isoformat(),
                equity=starting_balance,
            )
        )

        for deal_time, net in normalized_rows:
            running_net += net
            points.append(
                DashboardEquityPoint(
                    timestamp=datetime.fromtimestamp(deal_time).isoformat(),
                    equity=starting_balance + running_net,
                )
            )

        history_span_seconds = float(max(0, normalized_rows[-1][0] - normalized_rows[0][0]))
        return DashboardEquityCurveResponse(
            points=points,
            history_span_seconds=history_span_seconds,
            point_count=len(points),
        )
    except Exception as e:
        logger.error(f"Error building equity curve: {e}")
        return DashboardEquityCurveResponse(points=[], history_span_seconds=0.0, point_count=0)


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(authorization: Annotated[Optional[str], Header()] = None):
    """Return dashboard summary metrics backed by live MT5 and session data."""
    user_id = _get_authenticated_user_id(authorization)

    if user_id:
        _update_mt5_connection(user_id)

    daily_points: list[DashboardDailyPnlPoint] = []
    weekly_total = 0.0
    weekly_best = 0.0
    weekly_worst = 0.0
    win_rate = 0.0
    closed_trade_count = 0
    winning_trade_count = 0
    active_strategy_rows: list[DashboardActiveStrategyItem] = []

    try:
        today = datetime.now().date()
        pnl_by_day = {
            (today - timedelta(days=offset)): 0.0 for offset in range(6, -1, -1)
        }

        if client.is_connected():
            deals = client.history_deals_get(datetime(2000, 1, 1), datetime.now()) or []

            for deal in deals:
                deal_time = int(_coerce_deal_value(deal, "time", 0) or 0)
                if deal_time <= 0:
                    continue

                profit = float(_coerce_deal_value(deal, "profit", 0.0) or 0.0)
                commission = float(_coerce_deal_value(deal, "commission", 0.0) or 0.0)
                swap = float(_coerce_deal_value(deal, "swap", 0.0) or 0.0)
                net = profit + commission + swap
                deal_date = datetime.fromtimestamp(deal_time).date()

                if deal_date in pnl_by_day:
                    pnl_by_day[deal_date] += net

                if abs(net) > 1e-9:
                    closed_trade_count += 1
                    if net > 0:
                        winning_trade_count += 1

            if closed_trade_count > 0:
                win_rate = (winning_trade_count / closed_trade_count) * 100.0

        ordered_days = sorted(pnl_by_day.items(), key=lambda item: item[0])
        daily_points = [
            DashboardDailyPnlPoint(day=day.strftime("%a"), pnl=float(pnl))
            for day, pnl in ordered_days
        ]

        if daily_points:
            pnl_values = [point.pnl for point in daily_points]
            weekly_total = float(sum(pnl_values))
            weekly_best = float(max(pnl_values))
            weekly_worst = float(min(pnl_values))

        if user_id:
            sessions = db_manager.get_user_live_sessions(user_id) or []
            active_statuses = {"running", "paused"}

            for session in sessions:
                session_status = str(session.get("status", "") or "").lower()
                if session_status not in active_statuses:
                    continue

                strategies = db_manager.get_session_strategies(int(session["session_id"])) or []
                for strategy in strategies:
                    symbols = strategy.get("symbols") or []
                    timeframes = strategy.get("timeframes") or []
                    market = ", ".join(str(symbol) for symbol in symbols) if symbols else "-"
                    timeframe = ", ".join(str(value) for value in timeframes) if timeframes else "-"
                    active_strategy_rows.append(
                        DashboardActiveStrategyItem(
                            name=str(strategy.get("strategy_name") or "Unknown"),
                            market=market,
                            status=str(session.get("status") or "unknown").title(),
                            timeframe=timeframe,
                            session_name=str(session.get("session_name") or "Session"),
                        )
                    )

        return DashboardSummaryResponse(
            daily_pnl=daily_points,
            weekly_pnl_total=weekly_total,
            weekly_best_day=weekly_best,
            weekly_worst_day=weekly_worst,
            win_rate=win_rate,
            closed_trade_count=closed_trade_count,
            winning_trade_count=winning_trade_count,
            active_strategy_count=len(active_strategy_rows),
            active_strategies=active_strategy_rows,
        )
    except Exception as e:
        logger.error(f"Error building dashboard summary: {e}")
        return DashboardSummaryResponse(
            daily_pnl=daily_points,
            weekly_pnl_total=weekly_total,
            weekly_best_day=weekly_best,
            weekly_worst_day=weekly_worst,
            win_rate=win_rate,
            closed_trade_count=closed_trade_count,
            winning_trade_count=winning_trade_count,
            active_strategy_count=0,
            active_strategies=[],
        )


