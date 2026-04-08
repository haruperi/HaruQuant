from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.contracts.evaluation_report.model import EvaluationReport, EvaluationReportPayload


EXAMPLES_ROOT = (
    Path(__file__).resolve().parents[3]
    / "backend"
    / "contracts"
    / "evaluation_report"
    / "examples"
)


def _load_example(*parts: str) -> dict:
    return json.loads((EXAMPLES_ROOT.joinpath(*parts)).read_text(encoding="utf-8"))


def test_evaluation_report_accepts_valid_example():
    contract = EvaluationReport.model_validate(_load_example("valid", "workflow_pass.json"))

    assert contract.contract_type == "EvaluationReport"
    assert contract.payload.verdict == "pass"
    assert contract.payload.overall_score == 0.945


def test_evaluation_report_rejects_invalid_verdict():
    with pytest.raises(ValidationError):
        EvaluationReport.model_validate(_load_example("invalid", "bad_verdict.json"))


def test_evaluation_report_payload_requires_evaluator_identity():
    with pytest.raises(ValidationError):
        EvaluationReportPayload(
            evaluation_id="eval_01",
            target_type="workflow",
            target_ref="wf_01",
            rubric_name="trade_review_rubric",
            rubric_scores={"schema_compliance": 0.98},
            overall_score=0.945,
            verdict="pass",
            evaluation_model_id="gpt-5.4-mini",
        )
