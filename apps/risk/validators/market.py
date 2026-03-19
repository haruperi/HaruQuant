"""Market data validators for the canonical risk state."""

from __future__ import annotations

from typing import Dict, Iterable

from apps.utils.data_validator import DataValidator

from apps.risk.models.market_state import MarketState
from apps.risk.models.position_state import PositionState
from apps.risk.validators.common import ValidationSummary


def validate_market_states(
    markets: Dict[str, MarketState],
    positions: Iterable[PositionState],
    require_synchronized_coverage: bool = True,
) -> ValidationSummary:
    """Validate market slices using the shared utility validator where possible."""
    summary = ValidationSummary()
    validator = DataValidator()
    active_symbols = [position.symbol for position in positions]
    row_counts: Dict[str, int] = {}

    for symbol in active_symbols:
        if symbol not in markets:
            summary = summary.add(
                "error",
                "market_data_missing",
                "Active position is missing market data.",
                symbol=symbol,
            )
            continue

        market = markets[symbol]
        try:
            prepared = validator.prepare_data(market.bars)
            is_valid, _, issues = validator.validate_price_sanity(
                prepared,
                mark_invalid=True,
            )
        except Exception as exc:
            summary = summary.add(
                "error",
                "market_data_invalid",
                "Market data could not be prepared for risk processing.",
                symbol=symbol,
                error=str(exc),
            )
            continue

        row_counts[symbol] = int(len(prepared))
        if row_counts[symbol] == 0:
            summary = summary.add(
                "error",
                "market_data_empty",
                "Prepared market data is empty.",
                symbol=symbol,
            )

        if not is_valid:
            summary = summary.add(
                "error",
                "market_price_sanity_failed",
                "Market data failed price sanity checks.",
                symbol=symbol,
                issues=issues,
            )

    if require_synchronized_coverage and len(row_counts) > 1:
        unique_counts = set(row_counts.values())
        if len(unique_counts) != 1:
            summary = summary.add(
                "warning",
                "market_data_unsynchronized",
                "Active symbols do not have synchronized market coverage length.",
                row_counts=row_counts,
            )

    return summary
