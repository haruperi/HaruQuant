from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from contracts.common import Originator
from contracts.execution_intent.model import ExecutionIntent, ExecutionIntentPayload
from haruquant.execution import ExecutionSendService
from haruquant.execution import ShadowExecutionRequest, ShadowExecutionService


class FakeBrokerGateway:
    def __init__(self) -> None:
        self.called = False

    def place_order(self, request: dict[str, object]) -> dict[str, object]:
        self.called = True
        return {"retcode": 10009, "request": request}

    def modify_position(self, request: dict[str, object]) -> dict[str, object]:
        self.called = True
        return {"retcode": 10009, "request": request}

    def partial_close(self, request: dict[str, object]) -> dict[str, object]:
        self.called = True
        return {"retcode": 10009, "request": request}

    def full_close(self, request: dict[str, object]) -> dict[str, object]:
        self.called = True
        return {"retcode": 10009, "request": request}

    def cancel_order(self, request: dict[str, object]) -> dict[str, object]:
        self.called = True
        return {"retcode": 10009, "request": request}


def _intent() -> ExecutionIntent:
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
            broker_action_type="submit_order",
            symbol="EURUSD",
            side="buy",
            size={"units": 1000},
            order_type="market",
            price_params={"entry_price": 1.1},
            sl_tp_params={},
            idempotency_key="idem_001",
            expiry_time=datetime(2026, 4, 9, 10, 5, tzinfo=timezone.utc),
            pre_send_validation_snapshot_ref="snap_001",
        ),
    )


def test_shadow_execution_service_blocks_broker_side_effects_in_shadow_mode() -> None:
    gateway = FakeBrokerGateway()
    service = ShadowExecutionService(ExecutionSendService(gateway))

    decision = service.execute(
        ShadowExecutionRequest(
            intent=_intent(),
            shadow_enabled=True,
        )
    )

    assert decision.blocked_side_effects is True
    assert decision.result is None
    assert decision.reason == "shadow_mode_blocks_broker_side_effects"
    assert gateway.called is False


def test_shadow_execution_service_delegates_to_live_send_when_shadow_disabled() -> None:
    gateway = FakeBrokerGateway()
    service = ShadowExecutionService(ExecutionSendService(gateway))

    decision = service.execute(
        ShadowExecutionRequest(
            intent=_intent(),
            shadow_enabled=False,
        )
    )

    assert decision.blocked_side_effects is False
    assert decision.result is not None
    assert decision.reason == "live_send_allowed"
    assert gateway.called is True
