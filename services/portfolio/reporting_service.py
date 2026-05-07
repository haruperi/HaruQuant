"""Portfolio performance reporting service."""
from typing import Any
from agents._shared.persistence import utc_stamp, write_json_artifact
from agents.portfolio.shared.contracts import PerformanceReport

class ReportingService:
    def generate(self, *, report_type: str, data: dict[str, Any]) -> PerformanceReport:
        missing = [key for key in ["portfolio_pnl", "drawdown", "trade_count"] if key not in data]
        status = "incomplete" if missing or data.get("audit_gaps") or data.get("execution_logs_missing") else "complete"
        decisions = list(data.get("decision_required", []))
        if data.get("critical_audit_findings"):
            decisions.append("critical_audit_or_risk_findings")
        report = PerformanceReport(report_type=report_type, status=status, portfolio_pnl=float(data.get("portfolio_pnl", 0.0)), drawdown=float(data.get("drawdown", 0.0)), trade_count=int(data.get("trade_count", 0)), strategy_health=data.get("strategy_health", {}), decision_required=decisions, evidence_refs=data.get("evidence_refs", []))
        report.audit_ref = write_json_artifact("reports/portfolio", f"{report_type}-report-{utc_stamp()}.json", report.model_dump() if hasattr(report, "model_dump") else report.dict())
        return report
