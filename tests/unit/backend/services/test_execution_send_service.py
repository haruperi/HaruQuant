from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.contracts.common import Originator
from backend.contracts.execution_intent.model import ExecutionIntent, ExecutionIntentPayload
from haruquant.execution import ExecutionSendService


class FakeBrokerGateway:
    def __init__(self) -> None:
        self.requests: list[tuple[str, dict[str, object]]] = []

    def place_order(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(("place_order", request))
        return {"retcode": 10009, "order": 123, "request": request}

    def modify_position(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(("modify_position", request))
        return {"retcode": 10009, "order": 124, "request": request}

    def partial_close(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(("partial_close", request))
        return {"retcode": 10009, "order": 125, "request": request}

    def full_close(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(("full_close", request))
        return {"retcode": 10009, "order": 126, "request": request}

    def cancel_order(self, request: dict[str, object]) -> dict[str, object]:
        self.requests.append(("cancel_order", request))
        return {"retcode": 10009, "order": 127, "request": request}


@dataclass(frozen=True)
class FakeUnsupportedPayload:
    broker_action_type: str
    symbol: str = "EURUSD"
    side: str = "buy"
    order_type: str = "market"
    size: dict[str, object] = None  # type: ignore[assignment]
    price_params: dict[str, object] = None  # type: ignore[assignment]
    sl_tp_params: dict[str, object] = None  # type: ignore[assignment]
    idempotency_key: str = "idem_001"

    def __post_init__(self) -> None:
        object.__setattr__(self, "size", {"units": 1000} if self.size is None else self.size)
        object.__setattr__(self, "price_params", {} if self.price_params is None else self.price_params)
        object.__setattr__(self, "sl_tp_params", {} if self.sl_tp_params is None else self.sl_tp_params)


@dataclass(frozen=True)
class FakeUnsupportedIntent:
    payload: FakeUnsupportedPayload


def _intent(
    *,
    broker_action_type: str = "submit_order",
    size: dict[str, object] | None = None,
) -> ExecutionIntent:
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
            size=size or {"units": 1000},
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

    assert gateway.requests[0][0] == "place_order"
    assert gateway.requests[0][1]["symbol"] == "EURUSD"
    assert gateway.requests[0][1]["idempotency_key"] == "idem_001"
    assert result.broker_response["order"] == 123


def test_execution_send_service_supports_full_broker_action_set() -> None:
    gateway = FakeBrokerGateway()
    service = ExecutionSendService(gateway)

    service.send(_intent(broker_action_type="modify_order"))
    service.send(
        _intent(
            broker_action_type="close_position",
            size={"units": 1000, "close_fraction": 0.5},
        )
    )
    service.send(_intent(broker_action_type="close_position", size={"units": 1000}))
    service.send(_intent(broker_action_type="cancel_order"))

    assert [item[0] for item in gateway.requests] == [
        "modify_position",
        "partial_close",
        "full_close",
        "cancel_order",
    ]


def test_execution_send_service_rejects_unknown_action_type() -> None:
    gateway = FakeBrokerGateway()

    try:
        ExecutionSendService(gateway).send(
            FakeUnsupportedIntent(payload=FakeUnsupportedPayload(broker_action_type="unsupported_action"))
        )
    except ValueError as exc:
        assert "unsupported broker_action_type" in str(exc)
    else:
        raise AssertionError("expected unsupported action type failure")
