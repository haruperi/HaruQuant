from __future__ import annotations

import pytest

from backend.agents import (
    EvaluatorRubric,
    EvaluatorRubricCriterion,
    TrajectoryEvaluationService,
    detect_unsupported_assertions,
    generate_refinement_recommendations,
)


def test_evaluator_rubric_model_rejects_invalid_weights() -> None:
    with pytest.raises(ValueError, match="criterion weight must be positive"):
        EvaluatorRubricCriterion(name="grounding", weight=0, passing_score=0.8)


def test_trajectory_evaluation_service_scores_weighted_rubric() -> None:
    rubric = EvaluatorRubric(
        rubric_name="research_quality",
        criteria=(
            EvaluatorRubricCriterion(name="grounding", weight=2.0, passing_score=0.8),
            EvaluatorRubricCriterion(name="freshness", weight=1.0, passing_score=0.7),
        ),
    )

    evaluation = TrajectoryEvaluationService().evaluate(
        rubric=rubric,
        scores={"grounding": 0.9, "freshness": 0.6},
    )

    assert round(evaluation.overall_score, 2) == 0.8
    assert evaluation.verdict == "warning"


def test_detect_unsupported_assertions_flags_claims_without_evidence() -> None:
    check = detect_unsupported_assertions(
        claims=("Macro shock guaranteed",),
        evidence_refs=(),
    )

    assert check.supported is False
    assert check.unsupported_claims == ("Macro shock guaranteed",)


def test_generate_refinement_recommendations_uses_scores_and_assertions() -> None:
    rubric = EvaluatorRubric(
        rubric_name="research_quality",
        criteria=(
            EvaluatorRubricCriterion(name="grounding", weight=1.0, passing_score=0.8),
        ),
    )
    evaluation = TrajectoryEvaluationService().evaluate(
        rubric=rubric,
        scores={"grounding": 0.4},
    )
    check = detect_unsupported_assertions(
        claims=("Unsupported claim",),
        evidence_refs=(),
    )

    recommendation = generate_refinement_recommendations(
        evaluation=evaluation,
        unsupported_assertions=check,
    )

    assert "grounding" in recommendation.focus_areas
    assert len(recommendation.improvement_actions) == 2
