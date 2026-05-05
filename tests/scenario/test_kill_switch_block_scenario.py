from __future__ import annotations

from backend.orchestration.workflow import KillSwitchState
from services.risk.safety import evaluate_new_entry_block


def test_live_entry_blocked_when_kill_switch_triggered() -> None:
    block = evaluate_new_entry_block(KillSwitchState.HARD_TRIGGERED)

    assert block.blocked is True
    assert block.allow_force_exit is True
    assert block.reason_codes == ("kill_switch_blocks_new_entries",)

