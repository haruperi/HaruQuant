from __future__ import annotations

from backend.common.logging import WorkflowLogContext, bind_log_context, get_service_logger


def test_workflow_log_context_serializes_non_empty_fields():
    context = WorkflowLogContext(
        workflow_id="wf_123",
        correlation_id="corr_123",
        run_id="run_123",
        service="workflow_orchestrator",
    )

    payload = context.to_log_extra()

    assert payload["workflow_id"] == "wf_123"
    assert payload["correlation_id"] == "corr_123"
    assert payload["run_id"] == "run_123"
    assert payload["service"] == "workflow_orchestrator"
    assert "trace_id" not in payload


def test_get_service_logger_binds_component():
    logger = get_service_logger("risk_service")

    assert logger._bound_extra["component"] == "risk_service"


def test_bind_log_context_adds_standard_fields():
    logger = get_service_logger("workflow_orchestrator")
    context = WorkflowLogContext(
        workflow_id="wf_555",
        correlation_id="corr_555",
        trace_id="trace_555",
        environment="paper",
    )

    with bind_log_context(logger, context, stage="plan") as bound:
        assert bound._bound_extra["component"] == "workflow_orchestrator"
        assert bound._bound_extra["workflow_id"] == "wf_555"
        assert bound._bound_extra["correlation_id"] == "corr_555"
        assert bound._bound_extra["trace_id"] == "trace_555"
        assert bound._bound_extra["environment"] == "paper"
        assert bound._bound_extra["stage"] == "plan"
