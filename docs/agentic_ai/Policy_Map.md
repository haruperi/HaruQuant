# Policy Map (Playbook §12)

| Policy Name | Scope | Owner | Enforcement Layers | Failure Behavior | Logging | Exception Process | Review Cadence |
|---|---|---|---|---|---|---|---|
| trade_execution_policy | execution_workflows | risk_team | routing, orchestrator, execution_mcp | reject_and_escalate | audit_log_required | risk_committee_approval | monthly |
| risk_override_policy | risk_workflows | risk_team | orchestrator, risk_engine | reject_and_escalate | audit_log_required | cto_and_cro_approval | monthly |
| data_access_policy | data_workflows | data_team | routing, mcp_server | reject_and_log | standard_log | data_owner_approval | quarterly |
| model_usage_policy | agent_workflows | ai_team | orchestrator, agent | fallback_to_safe_model | audit_log_required | ai_lead_approval | monthly |
| approval_policy | all_workflows | compliance_team | orchestrator, approval_service | block_and_notify | audit_log_required | compliance_officer_override | monthly |
| escalation_policy | all_workflows | operations_team | orchestrator, monitoring | escalate_to_oncall | audit_log_required | incident_commander_decision | monthly |
| retention_policy | all_workflows | compliance_team | observability, storage | retain_until_review | audit_log_required | legal_hold_override | quarterly |
| input_output_policy | api_workflows | platform_team | api_gateway, routing, orchestrator | reject_and_log | standard_log | none | monthly |
| tool_use_policy | agent_workflows | ai_team | agent, mcp_server | deny_and_escalate | audit_log_required | ai_lead_approval | monthly |
