"""Portfolio incident reporting service."""
from typing import Any
from agents._shared.persistence import utc_stamp, write_json_artifact
from agents.portfolio.shared.contracts import IncidentReport

class IncidentService:
    def create_incident(self, **kwargs: Any) -> IncidentReport:
        report = IncidentReport(**kwargs)
        report.audit_ref = write_json_artifact("reports/logs/portfolio", f"incident-{utc_stamp()}.json", report.model_dump() if hasattr(report, "model_dump") else report.dict())
        return report
