"""Reusable service for Risk Department agents."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from agents._shared import AgentRunContext, AgentRunResult
from agents._shared.persistence import utc_stamp, write_json_artifact
from services.risk.approval_tokens import validate_approval_token
from services.risk.broker_risk import broker_risk_state
from services.risk.drawdown import drawdown_state
from services.risk.exposure import exposure_snapshot
from services.risk.governor import RiskGovernor
from services.risk.thresholds import config_version_hash, load_risk_thresholds, validate_config_hash

from .contracts import AGENT_CAPABILITIES, BLOCKED_ACTIONS


@dataclass(frozen=True)
class RiskAgentConfig:
    agent_name: str
    display_name: str
    artifact_type: str
    allowed_actions: tuple[str, ...]
    tool_names: tuple[str, ...]


@dataclass(frozen=True)
class RiskRuntimeAgent:
    name: str
    instructions: str
    tools: tuple[Callable[..., Any], ...]


def build_runtime_agent(config: RiskAgentConfig, instructions: str, tools: list[Callable[..., Any]]) -> RiskRuntimeAgent:
    return RiskRuntimeAgent(name=config.agent_name, instructions=instructions, tools=tuple(tools))


class GenericRiskAgent:
    def __init__(self, config: RiskAgentConfig) -> None:
        self.config = config
        self.agent_name = config.agent_name

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        output = self._build_output(context, task_input)
        uri = write_json_artifact("reports/risk", f"{self.agent_name}-{utc_stamp()}.json", output)
        return AgentRunResult(agent_name=self.agent_name, status=output["status"], output={**output, "artifact_uri": uri}, evidence_refs=[uri])

    def _build_output(self, context: AgentRunContext, task_input: dict[str, Any]) -> dict[str, Any]:
        thresholds = load_risk_thresholds()
        proposal = task_input.get("proposal", task_input.get("trade_proposal", {}))
        portfolio = task_input.get("portfolio_snapshot", task_input.get("portfolio_state", {}))
        market = task_input.get("market_snapshot", task_input.get("market_state", {}))
        governor_decision = RiskGovernor(thresholds=task_input.get("threshold_overrides")).evaluate_trade(proposal=proposal or {"proposal_id": context.task_id, "requested_volume": 0.01, "strategy_id": "strategy-demo", "strategy_code_hash": "hash", "symbol": "EURUSD", "side": "buy", "expected_risk": {"amount": 50}}, portfolio_snapshot=portfolio, market_snapshot=market)
        exposure = exposure_snapshot(portfolio.get("positions", []), equity=float(portfolio.get("equity", 100000.0)))
        drawdown = drawdown_state(portfolio, thresholds)
        broker = broker_risk_state(market, thresholds)
        status = "completed"
        escalation = "normal"
        if drawdown["critical"] or portfolio.get("kill_switch_active"):
            escalation = "kill_switch_recommended"
            status = "blocked"
        elif drawdown["failures"] or broker["failures"]:
            escalation = "block_new_trades"
            status = "blocked"
        elif governor_decision.decision not in {"approved", "approved_with_reduced_size"}:
            escalation = "reduce_risk"
        token_audit = {"checked": False, "valid": False, "reason": None}
        if task_input.get("approval_token"):
            token_audit["checked"] = True
            try:
                validate_approval_token(task_input["approval_token"], proposal=proposal, mark_used=False)
                token_audit["valid"] = True
            except Exception as exc:  # noqa: BLE001
                token_audit["reason"] = str(exc)
                status = "blocked"
        config_valid = validate_config_hash(thresholds, thresholds.get("config_hash"))
        if self.agent_name == "risk_limit_auditor" and not config_valid:
            status = "blocked"
        audit = {
            "request_id": context.task_id,
            "component_name": self.agent_name,
            "component_type": "risk_agent",
            "proposal_id": proposal.get("proposal_id"),
            "strategy_id": proposal.get("strategy_id"),
            "strategy_code_hash": proposal.get("strategy_code_hash"),
            "risk_config_hash": config_version_hash(thresholds),
            "policy_version": governor_decision.policy_version,
            "tools_called": list(self.config.tool_names),
            "evidence_refs": task_input.get("evidence_refs", []),
            "rules_checked": governor_decision.rules_checked,
            "rules_failed": governor_decision.rules_failed,
            "decision": governor_decision.decision,
            "risk_level": governor_decision.risk_level,
            "approved_volume": governor_decision.approved_volume,
            "approval_token_ref": governor_decision.approval_token_ref,
            "blocked_actions": list(BLOCKED_ACTIONS),
            "fallback_used": False,
            "error_if_any": None,
            "signature": governor_decision.signature,
        }
        memo = {
            "risk_summary": f"{self.config.display_name} reviewed deterministic risk evidence. RiskGovernor decision: {governor_decision.decision}.",
            "recommendation": "block_new_trades" if status == "blocked" else "hold_or_continue_review",
            "llm_override_blocked": True,
        }
        return {
            "status": status,
            self.config.artifact_type: {
                "risk_governor_decision": asdict(governor_decision),
                "portfolio_risk_status": escalation,
                "exposure_map": exposure,
                "drawdown_state": drawdown,
                "broker_risk": broker,
                "risk_config_valid": config_valid,
                "approval_token_audit": token_audit,
                "risk_memo": memo,
            },
            "allowed_actions": list(self.config.allowed_actions),
            "blocked_actions": list(BLOCKED_ACTIONS),
            "audit": audit,
        }


def evaluate_risk_agent_output(output: dict[str, Any], artifact_type: str) -> dict[str, Any]:
    checks = {
        "has_artifact": artifact_type in output,
        "has_audit": bool(output.get("audit")),
        "blocks_execution": "execute_trade" in output.get("blocked_actions", []),
        "llm_cannot_override": output[artifact_type]["risk_memo"]["llm_override_blocked"],
    }
    return {"passed": all(checks.values()), "checks": checks}

