"""Risk Reviewer Agent."""

from __future__ import annotations

from typing import Any

from agents._shared.persistence import utc_stamp, write_json_artifact
from agents._shared import AgentRunContext, AgentRunResult
from services.risk.domain.contracts import RiskMemo
from services.risk.governance.governor import RiskGovernorDecision


class RiskReviewerAgent:
    agent_name = "risk_reviewer"

    def create_risk_memo(
        self,
        *,
        strategy_summary: str,
        evidence_reviewed: list[str],
        risk_governor_output: RiskGovernorDecision | dict[str, Any],
        portfolio_impact: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        output = risk_governor_output if isinstance(risk_governor_output, dict) else risk_governor_output.__dict__
        reasons = output.get("reasons", output.get("rejection_reasons", []))
        decision = output.get("decision", "needs_more_context")
        recommendation = "reduce_or_reject" if reasons else "hold_or_promote_after_board_gate"
        if decision in {"rejected", "blocked", "error_fail_closed"}:
            recommendation = "block_new_trades"
        required_board_action = "required" if decision in {"approved", "approved_with_reduced_size"} else "blocked_until_risk_clear"
        memo = RiskMemo(
            memo_id=f"risk-memo-{utc_stamp()}",
            strategy_id=str(output.get("strategy_id", "strategy-unknown")),
            strategy_name=str(output.get("strategy_name", strategy_summary)),
            strategy_lifecycle_state=str(output.get("strategy_lifecycle_state", "unknown")),
            risk_governor_decision_ref=str(output.get("decision_id", output.get("approval_id", "risk-decision-unknown"))),
            evidence_reviewed=evidence_reviewed,
            risk_summary=f"RiskGovernor decision is {decision}. Supporting agents may explain this decision but cannot override it.",
            key_risk_metrics=output.get("risk_metrics_snapshot", {}),
            portfolio_impact=portfolio_impact or {},
            correlation_concerns=["correlated exposure must remain below policy"],
            drawdown_concerns=["daily, weekly, monthly, strategy, symbol, and portfolio drawdown gates are hard stops"],
            cost_concerns=["spread, slippage, commission, and swap assumptions must remain live-like"],
            margin_concerns=["free margin and margin level must remain above policy"],
            robustness_concerns=["failed robustness evidence blocks promotion"],
            statistical_concerns=["weak statistical evidence requires retest or paper-only treatment"],
            failure_modes=list(reasons),
            recommendation=recommendation,
            required_board_action=required_board_action,
            required_next_steps=["resolve_risk_rejections"] if reasons else ["retain_risk_governor_token_for_execution_handoff"],
            confidence="high" if output.get("signature") else "medium",
            evidence_refs=evidence_reviewed,
            audit={"risk_governor_decision": decision, "llm_override_blocked": True},
        )
        return memo.__dict__

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        memo = self.create_risk_memo(
            strategy_summary=task_input.get("strategy_summary", context.user_request),
            evidence_reviewed=task_input.get("evidence_reviewed", []),
            risk_governor_output=task_input.get("risk_governor_output", {}),
            portfolio_impact=task_input.get("portfolio_impact", {}),
        )
        uri = write_json_artifact("reports/risk", f"risk-memo-{utc_stamp()}.json", memo)
        return AgentRunResult(agent_name=self.agent_name, status="completed", output={**memo, "risk_memo_uri": uri}, evidence_refs=[uri])


__all__ = ["RiskReviewerAgent"]

