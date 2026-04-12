"""Persistence helpers for canonical risk decisions."""

from __future__ import annotations

import json
from pathlib import Path

from backend.data.database import RiskRepository

from .decisions import PackedRiskDecisionArtifacts


class RiskDecisionPersistenceService:
    """Persist canonical risk decisions and machine-enforceable constraints."""

    def __init__(self, db_path: str | Path) -> None:
        self.repository = RiskRepository(db_path)

    def save(self, *, risk_request_id: str, packed: PackedRiskDecisionArtifacts):
        """Persist the main decision row and any attached constraints."""

        decision = self.repository.create_decision(
            risk_decision_id=packed.contract.payload.risk_decision_id,
            risk_request_id=risk_request_id,
            proposal_id=packed.contract.payload.proposal_id,
            workflow_id=packed.contract.workflow_id,
            decision=packed.contract.payload.decision,
            rationale_text=packed.rationale_text,
            risk_metrics_snapshot_json=json.dumps(
                packed.risk_metrics_snapshot,
                sort_keys=True,
                separators=(",", ":"),
            ),
            freshness_expiry=packed.contract.payload.freshness_expiry.isoformat().replace("+00:00", "Z"),
            policy_version_id=packed.policy_version,
            formula_version=packed.formula_version,
            provenance_bundle_id=packed.provenance_bundle_id,
            approval_token=packed.contract.payload.approval_token,
        )
        constraints = tuple(
            self.repository.add_constraint(
                risk_decision_id=decision.risk_decision_id,
                constraint_type=constraint.constraint_type,
                constraint_value_json=json.dumps(
                    constraint.value,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
            for constraint in packed.contract.payload.limit_constraints
        )
        return decision, constraints


__all__ = ["RiskDecisionPersistenceService"]
