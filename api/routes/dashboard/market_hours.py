"""Market Hours API endpoint."""

from datetime import datetime, time, timedelta, timezone
from typing import List, Optional, TypedDict
from zoneinfo import ZoneInfo
from fastapi import APIRouter

from api.models import MarketHoursResponse, MarketStatus

router = APIRouter()


def is_market_open(
    current_time_local: datetime,
    open_time: time,
    close_time: time,
    lunch_start: Optional[time] = None,
    lunch_end: Optional[time] = None,
) -> bool:
    """Check if a market is open based on local time."""
    # Check if weekend
    if current_time_local.weekday() >= 5:  # 5=Saturday, 6=Sunday
        return False

    current_time = current_time_local.time()

    # Lunch break logic (e.g. Tokyo)
    if lunch_start and lunch_end:
        if open_time <= current_time < lunch_start:
            return True
        if lunch_end <= current_time < close_time:
            return True
        return False

    return open_time <= current_time < close_time


def format_timedelta(td: timedelta) -> str:
    """Format a timedelta as a short human-readable string."""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_market_message(
    current_time_local: datetime,
    open_time: time,
    close_time: time,
    lunch_start: Optional[time] = None,
    lunch_end: Optional[time] = None,
    is_open: bool = False,
):
    """Get a status message like "Opening in X" or "Closing in X"."""
    current_time = current_time_local.time()
    today_date = current_time_local.date()
    weekday = current_time_local.weekday()  # 0-6

    # If Open, calculate time until close (or lunch start)
    if is_open:
        # Check lunch start first
        if lunch_start and current_time < lunch_start:
            target = current_time_local.replace(
                hour=lunch_start.hour,
                minute=lunch_start.minute,
                second=0,
                microsecond=0,
            )
            diff = target - current_time_local
            return f"Lunch in {format_timedelta(diff)}"

        # Otherwise time until close
        target = current_time_local.replace(
            hour=close_time.hour, minute=close_time.minute, second=0, microsecond=0
        )
        diff = target - current_time_local

        # If result is negative, something is wrong or close is tomorrow (rare for stock markets to span midnight)
        if diff.total_seconds() < 0:
            return ""

        return f"Closing in {format_timedelta(diff)}"

    # If Closed, calculate time until Open
    else:
        # Weekend logic
        if weekday >= 5:  # Sat or Sun
            # Next open is Monday
            days_until_monday = 7 - weekday
            next_open_date = today_date + timedelta(days=days_until_monday)
            target = current_time_local.replace(
                year=next_open_date.year,
                month=next_open_date.month,
                day=next_open_date.day,
                hour=open_time.hour,
                minute=open_time.minute,
                second=0,
                microsecond=0,
            )
            diff = target - current_time_local
            return f"Opening in {format_timedelta(diff)}"

        # Weekday logic
        # 1. Before Open?
        if current_time < open_time:
            target = current_time_local.replace(
                hour=open_time.hour, minute=open_time.minute, second=0, microsecond=0
            )
            diff = target - current_time_local
            return f"Opening in {format_timedelta(diff)}"

        # 2. During Lunch? (Closed)
        if lunch_start and lunch_end and lunch_start <= current_time < lunch_end:
            target = current_time_local.replace(
                hour=lunch_end.hour, minute=lunch_end.minute, second=0, microsecond=0
            )
            diff = target - current_time_local
            return f"Opening in {format_timedelta(diff)}"

        # 3. After Close? -> Next day open
        if current_time >= close_time:
            next_day = today_date + timedelta(days=1)
            # Check if next day is weekend
            next_weekday = (weekday + 1) % 7
            if next_weekday >= 5:  # Friday night -> Monday morning
                next_day += timedelta(days=(7 - next_weekday))

            target = current_time_local.replace(
                year=next_day.year,
                month=next_day.month,
                day=next_day.day,
                hour=open_time.hour,
                minute=open_time.minute,
                second=0,
                microsecond=0,
            )
            diff = target - current_time_local
            return f"Opening in {format_timedelta(diff)}"

    return ""


@router.get("/market-hours", response_model=MarketHoursResponse)
async def get_market_hours():
    """Get status of major financial markets."""
    utc_now = datetime.now(timezone.utc)

    class MarketConfig(TypedDict, total=False):
        name: str
        timezone: str
        open: time
        close: time
        display_open: str
        display_close: str
        lunch_start: time
        lunch_end: time

    markets_config: List[MarketConfig] = [
        {
            "name": "London",
            "timezone": "Europe/London",
            "open": time(8, 0),
            "close": time(16, 30),
            "display_open": "08:00",
            "display_close": "16:30",
        },
        {
            "name": "New York",
            "timezone": "America/New_York",
            "open": time(9, 30),
            "close": time(16, 0),
            "display_open": "09:30",
            "display_close": "16:00",
        },
        {
            "name": "Tokyo",
            "timezone": "Asia/Tokyo",
            "open": time(9, 0),
            "close": time(15, 0),
            "lunch_start": time(11, 30),
            "lunch_end": time(12, 30),
            "display_open": "09:00",
            "display_close": "15:00",
        },
        {
            "name": "Sydney",
            "timezone": "Australia/Sydney",
            "open": time(10, 0),
            "close": time(16, 0),
            "display_open": "10:00",
            "display_close": "16:00",
        },
    ]

    market_statuses = []

    for market in markets_config:
        tz = ZoneInfo(market["timezone"])
        local_now = utc_now.astimezone(tz)

        is_open = is_market_open(
            local_now,
            market["open"],
            market["close"],
            market.get("lunch_start"),
            market.get("lunch_end"),
        )

        msg = get_market_message(
            local_now,
            market["open"],
            market["close"],
            market.get("lunch_start"),
            market.get("lunch_end"),
            is_open,
        )

        # specific open/close datetimes for 'today' in that market's timezone
        # We use these to send a robust timestamp to the frontend
        # so it can convert to the USER's local time.
        today_date = local_now.date()

        # Combine date and time, and localize
        open_dt = datetime.combine(today_date, market["open"], tzinfo=tz)
        close_dt = datetime.combine(today_date, market["close"], tzinfo=tz)

        market_statuses.append(
            MarketStatus(
                name=market["name"],
                status="Open" if is_open else "Closed",
                message=msg,
                # Send ISO format (result is UTC-aware or offset-aware)
                # Frontend will new Date(iso_string) and convert to local
                open=open_dt.isoformat(),
                close=close_dt.isoformat(),
                local_time=local_now.strftime("%H:%M:%S"),
            )
        )

    return MarketHoursResponse(markets=market_statuses)

