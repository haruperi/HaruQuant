"""
Trade gateway for live or simulated trading.

Provides a single entry point that returns CTrade bound to MT5 or simulator.
"""

from __future__ import annotations

from apps.ctrade import CTrade
from apps.simulator.engine import TradeSimulator


class TradeGateway:
    """Create a CTrade instance bound to live MT5 or a simulator."""

    def __init__(self, simulator: TradeSimulator | None = None) -> None:
        """Initialize the gateway."""
        self._simulator = simulator

    def get_trade(self, is_tester: bool = False) -> CTrade:
        """Return CTrade configured for live MT5 or simulator."""
        if is_tester:
            if self._simulator is None:
                raise ValueError("Simulator instance required for tester mode.")
            self._simulator.start(is_tester=True)
            return CTrade(api=self._simulator)
        if self._simulator is not None:
            self._simulator.start(is_tester=False)
        return CTrade()
