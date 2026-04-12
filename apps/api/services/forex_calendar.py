"""Helpers for retrieving Forex Factory calendar export data."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from io import StringIO
import json
from pathlib import Path
from typing import Any, Dict, List

import requests

FOREX_FACTORY_WEEKLY_EXPORT_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
FOREX_FACTORY_WEEKLY_EXPORT_CSV_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.csv"
REQUEST_TIMEOUT_SECONDS = 20
CACHE_TTL_SECONDS = 300
CACHE_PATH = Path("backend/data/cache/forex_factory_calendar_thisweek.json")

RangeKey = str


def _parse_event_datetime(value: str) -> datetime:
    """Parse Forex Factory export timestamps into timezone-aware datetimes."""
    return datetime.fromisoformat(value)


def _parse_csv_datetime(date_value: str, time_value: str) -> datetime:
    """Parse CSV export date and time into a timezone-aware datetime."""
    clean_date = (date_value or "").strip()
    clean_time = (time_value or "").strip() or "12:00am"

    if clean_time.lower() == "all day":
        clean_time = "12:00am"

    parsed = datetime.strptime(f"{clean_date} {clean_time.lower()}", "%m-%d-%Y %I:%M%p")
    return parsed.replace(tzinfo=timezone.utc)


def _format_event_day(value: datetime) -> str:
    """Format the event day without platform-specific strftime flags."""
    return f"{value.strftime('%a %b')} {value.day}"


def _format_event_clock(value: datetime) -> str:
    """Format the event time without platform-specific strftime flags."""
    hour = value.hour % 12 or 12
    suffix = "am" if value.hour < 12 else "pm"
    return f"{hour}:{value.strftime('%M')}{suffix}"


def _serialize_event(raw_event: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    """Normalize one raw export row into the API shape used by the frontend."""
    event_at = _parse_event_datetime(str(raw_event.get("date") or ""))
    delta = event_at.astimezone(timezone.utc) - now

    return {
        "title": str(raw_event.get("title") or "").strip(),
        "currency": str(raw_event.get("country") or "").strip(),
        "impact": str(raw_event.get("impact") or "").strip() or "Unknown",
        "forecast": str(raw_event.get("forecast") or "").strip() or "--",
        "previous": str(raw_event.get("previous") or "").strip() or "--",
        "event_time": event_at.isoformat(),
        "event_day": _format_event_day(event_at),
        "event_clock": _format_event_clock(event_at),
        "is_upcoming": delta.total_seconds() >= 0,
        "minutes_until": int(delta.total_seconds() // 60),
    }


def _format_next_event_label(event: Dict[str, Any] | None) -> str:
    """Build a compact label for the nearest upcoming event."""
    if not event:
        return "No upcoming event"
    return f"{event['currency']} {event['event_clock']} {event['title']}"


def _start_of_week(value: date) -> date:
    """Return Sunday as the start of the calendar week."""
    days_since_sunday = (value.weekday() + 1) % 7
    return value - timedelta(days=days_since_sunday)


def _end_of_week(value: date) -> date:
    """Return Saturday as the end of the calendar week."""
    return _start_of_week(value) + timedelta(days=6)


def _month_window(year: int, month: int) -> tuple[date, date]:
    """Return the first and last day of a month."""
    start = date(year, month, 1)
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return start, next_month - timedelta(days=1)


def _range_window(range_key: RangeKey, now: datetime) -> tuple[date, date]:
    """Resolve the date window for a supported range key."""
    today = now.date()

    if range_key == "today":
        return today, today
    if range_key == "tomorrow":
        target = today + timedelta(days=1)
        return target, target
    if range_key == "yesterday":
        target = today - timedelta(days=1)
        return target, target
    if range_key == "this_week":
        return _start_of_week(today), _end_of_week(today)
    if range_key == "next_week":
        start = _start_of_week(today) + timedelta(days=7)
        return start, start + timedelta(days=6)
    if range_key == "last_week":
        start = _start_of_week(today) - timedelta(days=7)
        return start, start + timedelta(days=6)
    if range_key == "next_month":
        year = today.year + (1 if today.month == 12 else 0)
        month = 1 if today.month == 12 else today.month + 1
        return _month_window(year, month)
    if range_key == "last_month":
        year = today.year - (1 if today.month == 1 else 0)
        month = 12 if today.month == 1 else today.month - 1
        return _month_window(year, month)
    if range_key == "up_next":
        return today, _end_of_week(today)
    return _start_of_week(today), _end_of_week(today)


def _range_label(range_key: RangeKey) -> str:
    """Convert a range key into a UI label."""
    return {
        "today": "Today",
        "tomorrow": "Tomorrow",
        "this_week": "This Week",
        "next_week": "Next Week",
        "next_month": "Next Month",
        "yesterday": "Yesterday",
        "up_next": "Up Next",
        "last_week": "Last Week",
        "last_month": "Last Month",
    }.get(range_key, "This Week")


def _normalize_json_export(raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalize JSON export rows into the internal raw event shape."""
    return [
        {
            "title": str(raw_event.get("title") or "").strip(),
            "country": str(raw_event.get("country") or "").strip(),
            "date": str(raw_event.get("date") or "").strip(),
            "impact": str(raw_event.get("impact") or "").strip(),
            "forecast": str(raw_event.get("forecast") or "").strip(),
            "previous": str(raw_event.get("previous") or "").strip(),
        }
        for raw_event in raw_events
    ]


def _normalize_csv_export(csv_text: str) -> List[Dict[str, Any]]:
    """Normalize CSV export rows into the internal raw event shape."""
    reader = csv.DictReader(StringIO(csv_text))
    normalized_rows: List[Dict[str, Any]] = []

    for row in reader:
        title = str(row.get("Title") or "").strip()
        date_value = str(row.get("Date") or "").strip()
        if not title or not date_value:
            continue

        event_at = _parse_csv_datetime(date_value, str(row.get("Time") or ""))
        normalized_rows.append(
            {
                "title": title,
                "country": str(row.get("Country") or "").strip(),
                "date": event_at.isoformat(),
                "impact": str(row.get("Impact") or "").strip(),
                "forecast": str(row.get("Forecast") or "").strip(),
                "previous": str(row.get("Previous") or "").strip(),
            }
        )

    return normalized_rows


def _build_response(
    raw_events: List[Dict[str, Any]],
    fetched_at: datetime,
    stale: bool,
    range_key: RangeKey,
) -> Dict[str, Any]:
    """Build the frontend response from raw export rows."""
    now = datetime.now(timezone.utc)
    all_events: List[Dict[str, Any]] = [
        _serialize_event(raw_event, now)
        for raw_event in raw_events
        if raw_event.get("title") and raw_event.get("date")
    ]

    range_start, range_end = _range_window(range_key, now)
    if range_key == "up_next":
        events = [
            event
            for event in all_events
            if event["is_upcoming"]
            and range_start <= _parse_event_datetime(event["event_time"]).date() <= range_end
        ]
    else:
        events = [
            event
            for event in all_events
            if range_start <= _parse_event_datetime(event["event_time"]).date() <= range_end
        ]

    impact_counts = Counter(event["impact"] for event in events)
    currencies = sorted({event["currency"] for event in events if event["currency"]})
    selected_range_count = sum(
        1
        for event in events
        if range_start <= _parse_event_datetime(event["event_time"]).astimezone(timezone.utc).date() <= range_end
    )
    upcoming_events = [event for event in events if event["is_upcoming"]]
    next_event = upcoming_events[0] if upcoming_events else None

    return {
        "source": "Forex Factory weekly export",
        "source_url": "https://www.forexfactory.com/calendar",
        "fetched_at": fetched_at.isoformat(),
        "stale": stale,
        "range": {
            "key": range_key,
            "label": _range_label(range_key),
            "start_date": range_start.isoformat(),
            "end_date": range_end.isoformat(),
        },
        "summary": {
            "total_events": len(events),
            "high_impact": impact_counts.get("High", 0),
            "medium_impact": impact_counts.get("Medium", 0),
            "low_impact": impact_counts.get("Low", 0),
            "currencies": len(currencies),
            "selected_events": selected_range_count,
            "next_event": _format_next_event_label(next_event),
        },
        "events": events,
    }


def _load_cache() -> Dict[str, Any] | None:
    """Load cached export rows from disk if available."""
    if not CACHE_PATH.exists():
        return None
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def _save_cache(raw_events: List[Dict[str, Any]], fetched_at: datetime) -> None:
    """Persist export rows to disk for short-term cache and stale fallback."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(
            {
                "fetched_at": fetched_at.isoformat(),
                "raw_events": raw_events,
            }
        ),
        encoding="utf-8",
    )


def _get_cached_response_if_fresh(
    cached_payload: Dict[str, Any] | None,
    range_key: RangeKey,
) -> Dict[str, Any] | None:
    """Return cached response when it is still within the TTL."""
    if not cached_payload:
        return None

    fetched_at = datetime.fromisoformat(cached_payload["fetched_at"])
    age_seconds = (datetime.now(timezone.utc) - fetched_at).total_seconds()
    if age_seconds > CACHE_TTL_SECONDS:
        return None

    raw_events = list(cached_payload.get("raw_events") or [])
    return _build_response(raw_events, fetched_at, stale=False, range_key=range_key)


def _get_stale_response(
    cached_payload: Dict[str, Any] | None,
    range_key: RangeKey,
) -> Dict[str, Any] | None:
    """Return a stale cached response when upstream retrieval fails."""
    if not cached_payload:
        return None

    fetched_at = datetime.fromisoformat(cached_payload["fetched_at"])
    raw_events = list(cached_payload.get("raw_events") or [])
    return _build_response(raw_events, fetched_at, stale=True, range_key=range_key)


def fetch_forex_factory_calendar(range_key: RangeKey = "this_week") -> Dict[str, Any]:
    """Fetch and normalize Forex Factory's weekly calendar export."""
    cached_payload = _load_cache()
    cached_response = _get_cached_response_if_fresh(cached_payload, range_key=range_key)
    if cached_response is not None:
        return cached_response

    session = requests.Session()
    session.trust_env = False
    try:
        response = session.get(
            FOREX_FACTORY_WEEKLY_EXPORT_URL,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()
        raw_events = _normalize_json_export(response.json())
        fetched_at = datetime.now(timezone.utc)
        _save_cache(raw_events, fetched_at)
        return _build_response(raw_events, fetched_at, stale=False, range_key=range_key)
    except Exception:
        try:
            response = session.get(
                FOREX_FACTORY_WEEKLY_EXPORT_CSV_URL,
                timeout=REQUEST_TIMEOUT_SECONDS,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            response.raise_for_status()
            raw_events = _normalize_csv_export(response.text)
            fetched_at = datetime.now(timezone.utc)
            _save_cache(raw_events, fetched_at)
            return _build_response(raw_events, fetched_at, stale=False, range_key=range_key)
        except Exception:
            stale_response = _get_stale_response(cached_payload, range_key=range_key)
            if stale_response is not None:
                return stale_response
            raise
