"""Usage example for kill-switch controller and safe-mode transitions."""

from __future__ import annotations

import sys
from pathlib import Path


def _load_engine() -> None:
    build_dir = Path(__file__).resolve().parents[3] / "build" / "bridge" / "Release"
    if build_dir.exists():
        sys.path.insert(0, str(build_dir))


def main() -> None:
    _load_engine()
    import hqt_engine

    risk = hqt_engine._risk
    ks = risk.KillSwitchController()

    print("initial:", ks.can_trade("alpha").state)

    ks.set_reduce_only("risk_reduction_mode")
    print("reduce_only:", ks.can_trade("alpha").policy_code)

    ks.trigger_strategy_kill_switch("alpha", "strategy_drawdown_limit")
    print("strategy_halt:", ks.can_trade("alpha").policy_code)

    ks.trigger_global_kill_switch("global_risk_limit")
    print("global_halt:", ks.can_trade("beta").policy_code)

    ks.request_emergency_shutdown("API", "operator_emergency_stop")
    emergency = ks.can_trade("beta")
    print("emergency:", emergency.policy_code, emergency.source)

    snapshot = ks.state_snapshot()
    print("snapshot:", snapshot.state, snapshot.emergency_shutdown, snapshot.last_reason)


if __name__ == "__main__":
    main()
