"""Continuous compliance Audit Agent."""

from __future__ import annotations

from typing import Any, Literal

from agents._shared.persistence import utc_stamp, write_json_artifact
from agents._shared import AgentRunContext, AgentRunResult

AuditSeverity = Literal["info", "warning", "major", "critical"]


class AuditAgent:
    agent_name = "audit"
    severities = ["info", "warning", "major", "critical"]

    def audit(self, *, records: dict[str, Any]) -> dict[str, Any]:
        findings: list[dict[str, Any]] = []
        for order in records.get("live_orders", []):
            approval = order.get("risk_approval")
            if not approval:
                findings.append({"severity": "critical", "check": "live_order_has_risk_governor_approval", "order_id": order.get("order_id")})
            elif approval.get("proposal_id") != order.get("proposal_id"):
                findings.append({"severity": "critical", "check": "approval_token_matches_order", "order_id": order.get("order_id")})
            if not order.get("broker_response"):
                findings.append({"severity": "major", "check": "broker_response_present", "order_id": order.get("order_id")})
        for strategy in records.get("strategies", []):
            if strategy.get("state") in {"micro_live", "limited_live", "normal_live"} and not strategy.get("board_approval"):
                findings.append({"severity": "critical", "check": "live_strategy_has_board_approval", "strategy_id": strategy.get("strategy_id")})
            if strategy.get("skipped_lifecycle_stage"):
                findings.append({"severity": "major", "check": "strategy_lifecycle_not_skipped", "strategy_id": strategy.get("strategy_id")})
        if records.get("risk_threshold_changed_by_agent"):
            findings.append({"severity": "critical", "check": "agents_cannot_change_risk_thresholds"})
        if records.get("missing_evidence_refs"):
            findings.append({"severity": "major", "check": "evidence_refs_present", "refs": records.get("missing_evidence_refs")})
        if records.get("hidden_failed_tool_calls"):
            findings.append({"severity": "major", "check": "no_hidden_failed_tool_calls"})
        if records.get("missing_execution_logs"):
            findings.append({"severity": "major", "check": "execution_logs_present"})
        critical = any(item["severity"] == "critical" for item in findings)
        report = {
            "report_type": "daily_audit",
            "findings": findings,
            "critical_audit_failure_disables_live_trading": critical,
            "live_trading_allowed": not critical,
        }
        report["audit_report_uri"] = write_json_artifact("reports/daily", f"audit-{utc_stamp()}.json", report)
        return report

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        report = self.audit(records=task_input)
        return AgentRunResult(agent_name=self.agent_name, status="completed", output=report, evidence_refs=[report["audit_report_uri"]])


__all__ = ["AuditAgent", "AuditSeverity"]
