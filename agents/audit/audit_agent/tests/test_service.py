from agents._shared import AgentRunContext
from agents.audit.audit_agent.service import AuditComplianceAgent

def test_service_reports_findings():
    result = AuditComplianceAgent().run(context=AgentRunContext(workflow_id="wf", task_id="task", user_request="audit"), task_input={"records": []})
    assert result.output["audit_ref"]
