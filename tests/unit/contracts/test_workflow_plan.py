from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.contracts.workflow_plan.model import WorkflowPlan, WorkflowPlanPayload


EXAMPLES_ROOT = Path(__file__).resolve().parents[3] / "backend" / "contracts" / "workflow_plan" / "examples"


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_workflow_plan_accepts_valid_example():
    contract = WorkflowPlan.model_validate(_load_example("valid", "trade_review_plan.json"))

    assert contract.contract_type == "WorkflowPlan"
    assert contract.payload.plan_id == "plan_01"
    assert len(contract.payload.phase_steps) == 2


def test_workflow_plan_rejects_missing_required_payload_field():
    with pytest.raises(ValidationError):
        WorkflowPlan.model_validate(_load_example("invalid", "missing_phase_steps.json"))


def test_workflow_plan_payload_requires_at_least_one_phase_step():
    with pytest.raises(ValidationError):
        WorkflowPlanPayload(
            plan_id="plan_01",
            selected_pattern="sequential_review",
            phase_steps=[],
        )
