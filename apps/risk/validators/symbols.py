"""Symbol specification validators for the canonical risk state."""

from __future__ import annotations

from typing import Dict, Iterable

from apps.risk.models.position_state import PositionState
from apps.risk.models.symbol_state import SymbolState
from apps.risk.validators.common import ValidationSummary


def validate_symbol_states(
    symbols: Dict[str, SymbolState],
    positions: Iterable[PositionState],
) -> ValidationSummary:
    """Validate symbol specifications required by existing risk math."""
    summary = ValidationSummary()
    active_symbols = {position.symbol for position in positions}

    for symbol in active_symbols:
        if symbol not in symbols:
            summary = summary.add(
                "error",
                "symbol_spec_missing",
                "Active position is missing symbol specification data.",
                symbol=symbol,
            )
            continue

        spec = symbols[symbol]
        if (
            not (spec.contract_size and spec.contract_size > 0)
            and not (
                spec.tick_value
                and spec.tick_value > 0
                and spec.tick_size
                and spec.tick_size > 0
            )
        ):
            summary = summary.add(
                "error",
                "symbol_spec_insufficient_risk_math",
                "Symbol spec requires contract_size or both tick_value and tick_size.",
                symbol=symbol,
            )

        if spec.volume_step is not None and spec.volume_step <= 0:
            summary = summary.add(
                "warning",
                "symbol_spec_invalid_volume_step",
                "volume_step should be positive when provided.",
                symbol=symbol,
                volume_step=spec.volume_step,
            )

    return summary
