"""Position-level validators for the canonical risk state."""

from __future__ import annotations

from typing import Iterable

from backend.services.risk_engine.models.position_state import PositionState
from backend.services.risk_engine.validators.common import ValidationSummary


def validate_position_states(positions: Iterable[PositionState]) -> ValidationSummary:
    """Validate normalized positions before portfolio-level risk math."""
    summary = ValidationSummary()

    for position in positions:
        if not position.symbol:
            summary = summary.add(
                "error",
                "position_missing_symbol",
                "Position symbol is required.",
            )

        if position.lots == 0:
            summary = summary.add(
                "warning",
                "position_zero_lots",
                "Zero-lot positions should normally be excluded from canonical state.",
                symbol=position.symbol,
            )

        if position.side not in {"LONG", "SHORT"}:
            summary = summary.add(
                "error",
                "position_invalid_side",
                "Position side must be LONG or SHORT.",
                symbol=position.symbol,
                side=position.side,
            )

    return summary
