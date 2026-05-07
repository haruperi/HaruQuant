"""Evidence requirements for executive workflows."""

WORKFLOW_EVIDENCE_REQUIREMENTS = {
    "research": ["research_request", "market_context", "evidence_refs", "audit_trace"],
    "strategy_creation": ["research_evidence_refs", "strategy_spec", "strategy_review", "audit_trace"],
    "simulation": ["strategy_code_hash", "market_data_manifest", "simulation_artifacts", "audit_trace"],
    "backtest_diagnosis": ["backtest_run_ref", "diagnostics", "audit_trace"],
    "optimization_comparison": ["candidate_runs", "robustness_metrics", "risk_review", "audit_trace"],
    "risk_review": ["strategy_spec", "simulation_evidence_package", "portfolio_snapshot", "risk_policy", "audit_trace"],
    "portfolio": ["strategy_lifecycle_state", "risk_governor_constraints", "portfolio_snapshot", "audit_trace"],
    "execution_proposal": ["trade_proposal", "risk_governor_decision", "board_approval", "audit_trace"],
    "reporting": ["report_inputs", "audit_trace"],
    "governed_action_draft": ["governance_context", "risk_policy", "audit_trace"],
}


def required_evidence_for(workflow_type: str) -> list[str]:
    return list(WORKFLOW_EVIDENCE_REQUIREMENTS.get(workflow_type, ["operator_request", "audit_trace"]))


def missing_evidence(required: list[str], evidence_refs: list[str]) -> list[str]:
    normalized = " ".join(evidence_refs).lower()
    return [item for item in required if item.lower() not in normalized]
