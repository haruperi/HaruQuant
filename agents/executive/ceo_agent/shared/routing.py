"""Executive workflow routing metadata."""

KNOWN_EXECUTIVE_WORKFLOWS = {
    "research",
    "strategy_creation",
    "strategy_codegen",
    "strategy_review",
    "backtest",
    "backtest_diagnosis",
    "optimization_comparison",
    "robustness_review",
    "statistical_validation",
    "risk_review",
    "portfolio",
    "portfolio_review",
    "allocation_review",
    "paper_trading_review",
    "execution_proposal",
    "reporting",
    "audit_review",
    "cost_review",
    "page_action",
    "clarification",
    "governed_action_draft",
    "ceo_answer",
    "ceo_identity",
}

FORBIDDEN_BACKEND_TOOLS = {
    "place_order",
    "close_position",
    "cancel_order",
    "modify_risk_thresholds",
    "enable_live_trading",
    "broker_mutation",
}


def unknown_workflow(workflow_type: str) -> bool:
    return workflow_type not in KNOWN_EXECUTIVE_WORKFLOWS


def forbidden_tools(tools: list[str]) -> list[str]:
    return [tool for tool in tools if tool in FORBIDDEN_BACKEND_TOOLS]
