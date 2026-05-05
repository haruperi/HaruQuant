from __future__ import annotations

from haruquant.execution import propagate_authority_state


def test_propagate_authority_state_maps_authoritative_badge() -> None:
    view = propagate_authority_state(
        has_receipt=True,
        receipt_authoritative_state="AUTHORITATIVE",
    )
    assert view.authority_state == "AUTHORITATIVE"


def test_propagate_authority_state_maps_reconciling_badge() -> None:
    view = propagate_authority_state(
        has_receipt=True,
        receipt_authoritative_state="PROVISIONAL",
        reconciliation_result_state="CONFLICTING",
    )
    assert view.authority_state == "RECONCILING"


def test_propagate_authority_state_defaults_to_provisional_badge() -> None:
    view = propagate_authority_state(has_receipt=False)
    assert view.authority_state == "PROVISIONAL"
