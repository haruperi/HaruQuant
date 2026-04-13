"""Risk governor agent metadata (deterministic — no LLM prompt needed).

The RiskGovernorAgent wraps a DeterministicRiskService protocol and does not
use LLM-based prompting. This file documents its role and behavior for the
agent catalog and prompt registry.
"""

# This is a deterministic adapter, not an LLM-driven agent.
# No instruction string is needed — the agent delegates to
# DeterministicRiskService.evaluate() which applies hard-coded
# risk limits and policy rules.

# Metadata for agent catalog registration:
RISK_GOVERNOR_METADATA = {
    "agent_name": "risk_governor_agent",
    "contract_type": "RiskAssessmentDecision",
    "is_llm_driven": False,
    "description": (
        "Deterministic risk evaluation adapter. Evaluates execution intents "
        "against risk limits (VaR, ES, margin, concentration) and returns "
        "APPROVE, REJECT, or ESCALATE decisions with evidence."
    ),
    "role": "Risk governance gate — evaluates all proposed trades against "
            "hard risk limits and policy rules before execution.",
    "tools": ["DeterministicRiskService.evaluate()"],
    "rules": [
        "VaR must be within configured cap (default: 10% of equity)",
        "Expected Shortfall must be within configured cap (default: 15% of equity)",
        "Margin utilization must be below configured threshold (default: 50%)",
        "Single-name concentration must be within limits (default: 20% of portfolio risk)",
        "Correlation limits must be respected",
    ],
    "escalation_conditions": [
        "VaR exceeds 90% of limit → ESCALATE",
        "ES exceeds limit → REJECT",
        "Margin exceeds 80% → ESCALATE",
        "Risk decision missing → ESCALATE",
    ],
    "failure_behavior": (
        "If risk service is unavailable, return ESCALATE with "
        "confidence=0.0 and explain service unavailability."
    ),
}
