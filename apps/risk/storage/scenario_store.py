"""Scenario-specific storage helpers."""

from __future__ import annotations

from collections.abc import Iterable

from apps.risk.scenarios import ScenarioResult

from .repositories import RiskRepository


class RiskScenarioStore:
    """Persist scenario outputs without the full snapshot-store surface area."""

    def __init__(self, repository: RiskRepository):
        self.repository = repository

    def store(
        self,
        *,
        snapshot_id: int,
        scenarios: Iterable[ScenarioResult],
    ) -> None:
        self.repository.db.save_risk_scenarios(
            snapshot_id=snapshot_id,
            scenarios=scenarios,
        )
