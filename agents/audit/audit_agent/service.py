from agents._shared import AgentRunContext, AgentRunResult
from agents._shared.persistence import utc_stamp, write_json_artifact
from .deterministic_policy import audit_policy
class AuditComplianceAgent:
    agent_name = "audit_agent"
    def run(self, *, context: AgentRunContext, task_input: dict) -> AgentRunResult:
        findings = audit_policy(task_input.get("records", []))
        payload = {"findings": [finding.model_dump() if hasattr(finding, "model_dump") else finding.dict() for finding in findings], "critical": any(f.severity == "critical" for f in findings)}
        audit_ref = write_json_artifact("reports/logs/audit", f"audit-agent-{utc_stamp()}.json", payload)
        return AgentRunResult(agent_name=self.agent_name, status="blocked" if payload["critical"] else "completed", output={**payload, "audit_ref": audit_ref}, evidence_refs=[audit_ref])
