"""Handoff helpers for Strategy Creation Department."""

from __future__ import annotations

from uuid import uuid4

from .contracts import StrategyCodePackage, StrategyHandoffPackage, StrategyLifecycleState, StrategyReviewReport, StrategySpec


def build_handoff_package(spec: StrategySpec, code: StrategyCodePackage, review: StrategyReviewReport) -> StrategyHandoffPackage:
    return StrategyHandoffPackage(
        handoff_id=str(uuid4()),
        spec_id=spec.spec_id,
        code_package_id=code.code_package_id,
        strategy_version=spec.version,
        generated_file_manifest=code.file_manifest,
        target_symbol=spec.symbol,
        target_timeframe=spec.timeframe,
        data_requirements=spec.data_requirements,
        cost_assumptions=spec.cost_assumptions,
        execution_assumptions=spec.execution_assumptions,
        risk_assumptions=spec.risk_controls,
        test_plan=spec.test_plan,
        robustness_requirements=spec.robustness_plan,
        research_evidence_refs=spec.evidence_refs,
        reviewer_status=review.review_status,
        known_limitations=review.non_blocking_issues,
        expected_failure_modes=spec.expected_failure_modes,
        lifecycle_state=StrategyLifecycleState.APPROVED_FOR_BACKTEST,
    )
