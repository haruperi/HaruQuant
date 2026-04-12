"""Registry helpers for deterministic stress scenarios."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List

from .models import StressScenario


@dataclass
class ScenarioRegistry:
    """Simple registry for deterministic scenario definitions."""

    scenarios: List[StressScenario] = field(default_factory=list)

    def register(self, scenario: StressScenario) -> None:
        self.scenarios.append(scenario)

    def extend(self, scenarios: Iterable[StressScenario]) -> None:
        self.scenarios.extend(scenarios)


def build_default_scenario_registry() -> ScenarioRegistry:
    """Build the default Phase 5 scenario registry."""
    registry = ScenarioRegistry()
    registry.extend(
        [
            StressScenario(
                name="volatility_shock",
                description="Scale portfolio volatility by a deterministic sigma multiplier.",
                parameters={"shock_sigma": 2.5},
            ),
            StressScenario(
                name="spread_blowout",
                description="Apply a spread widening cost to gross exposure.",
                parameters={"spread_bps": 20.0},
            ),
            StressScenario(
                name="gap_risk",
                description="Apply a deterministic gap move to the largest single-name exposure.",
                parameters={"gap_frac": 0.015},
            ),
            StressScenario(
                name="correlation_spike",
                description="Recompute tail loss under a stressed positive correlation floor.",
                parameters={"corr_floor": 0.85},
            ),
            StressScenario(
                name="liquidity_crunch",
                description="Apply a liquidation discount to gross exposure.",
                parameters={"liquidity_cost_frac": 0.0075},
            ),
        ]
    )
    return registry
