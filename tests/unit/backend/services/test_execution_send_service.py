from __future__ import annotations

from datetime import datetime, timezone

from backend.contracts.common import Originator
from backend.contracts.execution_intent.model import ExecutionIntent, ExecutionIntentPayload
from backend.services.execution.send_service import ExecutionSendService


class FakeBrokerGateway:
    def __init__(self) -> None:
        self.requests: list[dict[str, object]] = []

    def place_order(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(request)
        return {"retcode": 10009, "order": 123, "request": request}


def _intent(*, broker_action_type: str = "submit_order") -> ExecutionIntent:
    return ExecutionIntent(
        workflow_id="wf_001",
        correlation_id="corr_001",
        causation_id="evt_001",
        timestamp_utc="2026-04-09T10:00:00Z",
        originator=Originator(type="service", id="execution_agent"),
        environment="paper",
        operating_mode="MODE-002",
        payload=ExecutionIntentPayload(
            execution_intent_id="exec_001",
            proposal_id="prop_001",
            risk_decision_id="risk_001",
            broker_action_type=broker_action_type,
            symbol="EURUSD",
            side="buy",
            size={"units": 1000},
            order_type="market",
            price_params={"entry_rationale": "retest"},
            sl_tp_params={"stop_loss_logic": {"type": "swing_low"}},
            idempotency_key="idem_001",
            expiry_time=datetime(2026, 4, 9, 10, 5, tzinfo=timezone.utc),
            pre_send_validation_snapshot_ref="snap_001",
        ),
    )


def test_execution_send_service_submits_submit_order_requests() -> None:
    gateway = FakeBrokerGateway()
    result = ExecutionSendService(gateway).send(_intent())

    assert gateway.requests[0]["symbol"] == "EURUSD"
    assert gateway.requests[0]["idempotency_key"] == "idem_001"
    assert result.broker_response["order"] == 123


def test_execution_send_service_rejects_unsupported_action_type() -> None:
    gateway = FakeBrokerGateway()

    try:
        ExecutionSendService(gateway).send(_intent(broker_action_type="cancel_order"))
    except ValueError as exc:
        assert "unsupported broker_action_type" in str(exc)
    else:
        raise AssertionError("expected unsupported action type failure")
