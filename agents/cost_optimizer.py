"""Cost Optimizer Agent."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from agents._persistence import utc_stamp, write_json_artifact
from agents.base import AgentRunContext, AgentRunResult


class CostOptimizerAgent:
    agent_name = "cost_optimizer"

    model_routes = {
        "ceo_decision": "strong",
        "risk_memo": "strong",
        "code_generation": "coding",
        "report_formatting": "cheap",
        "simple_summary": "local",
        "risk_approval": "deterministic",
        "order_placement": "no_llm",
    }

    def summarize_costs(self, usage_records: list[dict[str, Any]]) -> dict[str, Any]:
        totals = defaultdict(float)
        accepted_cost = rejected_cost = live_candidate_cost = 0.0
        for record in usage_records:
            cost = float(record.get("cost", 0.0))
            totals["total_cost"] += cost
            totals[f"provider:{record.get('model_provider', 'unknown')}"] += cost
            totals[f"model:{record.get('model_name', 'unknown')}"] += cost
            totals[f"task:{record.get('task_id', 'unknown')}"] += cost
            totals[f"agent:{record.get('agent_name', 'unknown')}"] += cost
            totals[f"workflow:{record.get('workflow_id', 'unknown')}"] += cost
            totals[f"strategy:{record.get('strategy_id', 'unknown')}"] += cost
            totals["prompt_tokens"] += float(record.get("prompt_tokens", 0))
            totals["completion_tokens"] += float(record.get("completion_tokens", 0))
            if record.get("status") == "failed":
                totals["failed_call_cost"] += cost
            if record.get("compute_type") == "backtest":
                totals["backtest_compute_cost"] += cost
            if record.get("strategy_outcome") == "accepted":
                accepted_cost += cost
            if record.get("strategy_outcome") == "rejected":
                rejected_cost += cost
            if record.get("live_candidate"):
                live_candidate_cost += cost
        report = {
            "daily_cost_report": dict(totals),
            "weekly_cost_report": dict(totals),
            "cost_per_accepted_strategy": accepted_cost,
            "cost_per_rejected_strategy": rejected_cost,
            "cost_per_live_candidate": live_candidate_cost,
            "cost_anomaly_alerts": ["daily_budget_exceeded"] if totals["total_cost"] > 100 else [],
            "model_routes": self.model_routes,
        }
        report["cost_report_uri"] = write_json_artifact("reports/monthly", f"cost-{utc_stamp()}.json", report)
        return report

    def run(self, *, context: AgentRunContext, task_input: dict[str, Any]) -> AgentRunResult:
        report = self.summarize_costs(task_input.get("usage_records", []))
        return AgentRunResult(agent_name=self.agent_name, status="completed", output=report, evidence_refs=[report["cost_report_uri"]])


__all__ = ["CostOptimizerAgent"]
