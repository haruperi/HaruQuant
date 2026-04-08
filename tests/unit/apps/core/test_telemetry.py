from __future__ import annotations

from apps.core.telemetry import InMemoryTelemetry


def test_emit_event_records_attributes():
    telemetry = InMemoryTelemetry()

    event = telemetry.emit_event("workflow.created", workflow_id="wf_123", environment="test")

    assert event.name == "workflow.created"
    assert event.attributes["workflow_id"] == "wf_123"
    assert telemetry.events[0].attributes["environment"] == "test"


def test_increment_aggregates_by_name_and_attributes():
    telemetry = InMemoryTelemetry()

    telemetry.increment("workflow.transitions", workflow_type="trade_review")
    metric = telemetry.increment("workflow.transitions", workflow_type="trade_review")

    assert metric.value == 2
    assert telemetry.counters[0].name == "workflow.transitions"
    assert telemetry.counters[0].attributes["workflow_type"] == "trade_review"


def test_record_duration_persists_timer_metric():
    telemetry = InMemoryTelemetry()

    timer = telemetry.record_duration("risk.eval.latency", 12.5, environment="paper")

    assert timer.duration_ms == 12.5
    assert telemetry.timers[0].attributes["environment"] == "paper"


def test_span_records_elapsed_time():
    telemetry = InMemoryTelemetry()

    with telemetry.span("workflow.plan", workflow_id="wf_999"):
        pass

    assert telemetry.spans[0].name == "workflow.plan"
    assert telemetry.spans[0].duration_ms >= 0.0
    assert telemetry.spans[0].attributes["workflow_id"] == "wf_999"
