"""Portfolio cost governance service."""
from typing import Any
from agents._shared.persistence import utc_stamp, write_json_artifact
from agents.portfolio.shared.contracts import CostReport

class CostService:
    protected_decision_types = {"risk_governor", "order_router", "execution", "risk_approval"}
    def report(self, *, period: str, usage: list[dict[str, Any]], budget: float) -> CostReport:
        total = sum(float(item.get("cost", 0.0)) for item in usage)
        by_agent, by_provider, anomalies = {}, {}, []
        for item in usage:
            by_agent[item.get("agent", "unknown")] = by_agent.get(item.get("agent", "unknown"), 0.0) + float(item.get("cost", 0.0))
            by_provider[item.get("model_provider", "unknown")] = by_provider.get(item.get("model_provider", "unknown"), 0.0) + float(item.get("cost", 0.0))
            if item.get("task_type") in self.protected_decision_types and item.get("model_name") not in {None, "deterministic", "none"}:
                anomalies.append(f"protected_decision_routed_to_llm:{item.get('task_type')}")
        if total > budget:
            anomalies.append("budget_exceeded")
        report = CostReport(period=period, total_cost=total, budget=budget, by_agent=by_agent, by_model_provider=by_provider, anomalies=anomalies, recommendations=["use_cache_for_repeated_summaries", "batch_low_risk_reports"])
        report.audit_ref = write_json_artifact("reports/portfolio", f"cost-{period}-{utc_stamp()}.json", report.model_dump() if hasattr(report, "model_dump") else report.dict())
        return report
