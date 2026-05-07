"""Executive permission profiles."""

CEO_AGENT_PERMISSIONS = {
    "can_read_user_request": True,
    "can_call_internal_planner": True,
    "can_delegate_to_departments": True,
    "can_read_evidence": True,
    "can_write_executive_memo": True,
    "can_write_audit_record": True,
    "can_create_governed_action_draft": True,
    "can_request_board_approval": True,
    "can_execute_trade": False,
    "can_approve_risk": False,
    "can_override_risk_governor": False,
    "can_override_kill_switch": False,
    "can_modify_risk_thresholds": False,
    "can_enable_live_trading": False,
}

PLANNER_AGENT_PERMISSIONS = {
    "can_read_normalized_user_request": True,
    "can_read_capability_registry": True,
    "can_read_evidence_requirements": True,
    "can_read_policy_summaries": True,
    "can_propose_workflow_plan": True,
    "can_classify_intent": True,
    "can_identify_missing_inputs": True,
    "can_call_specialist_departments": False,
    "can_answer_user_directly": False,
    "can_execute_trade": False,
    "can_approve_risk": False,
    "can_mutate_state": False,
}
