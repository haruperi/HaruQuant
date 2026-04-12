"""Forex calendar dashboard route."""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from backend.api.services.forex_calendar import fetch_forex_factory_calendar

router = APIRouter()


@router.get("/forex-calendar")
async def get_forex_calendar(
    range_key: Literal[
        "today",
        "tomorrow",
        "this_week",
        "next_week",
        "next_month",
        "yesterday",
        "up_next",
        "last_week",
        "last_month",
    ] = Query(default="this_week"),
):
    """Return the normalized Forex Factory weekly calendar feed."""
    try:
        return fetch_forex_factory_calendar(range_key=range_key)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to retrieve Forex Factory calendar data: {exc}",
        ) from exc
