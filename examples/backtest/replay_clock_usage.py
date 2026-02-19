"""Usage example for deterministic replay hooks (IP-08)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_bridge_dir = ROOT / "build" / "bridge" / "Release"
if _bridge_dir.exists() and str(_bridge_dir) not in sys.path:
    sys.path.insert(0, str(_bridge_dir))

from apps.simulation.replay_hooks import compare_replay_runs, replay_fingerprint

try:
    import hqt_engine  # type: ignore
except Exception:
    hqt_engine = None  # type: ignore


def demo_cpp_replay_clock() -> None:
    print("--- C++ ReplayClock via bridge ---")
    if hqt_engine is None:
        print("hqt_engine not available. Build bridge to run C++ ReplayClock example.")
        return

    clock = hqt_engine.ReplayClock([1000, 2000, 3000, 4000])
    print("timeline signature:", clock.timeline_signature())
    print("peek next:", clock.peek_next())

    clock.pause()
    print("advance while paused:", clock.advance())
    print("step_by_bar(2) while paused:", clock.step_by_bar(2))
    clock.resume()
    print("advance after resume:", clock.advance())

    state = clock.state()
    print("state cursor:", state.cursor)
    print("state current_time_us:", state.current_time_us)


def main() -> None:
    demo_cpp_replay_clock()
    print("--- Python replay fingerprint hook ---")

    baseline = [
        {"timestamp": 1_700_000_000, "symbol": "EURUSD", "type": "bar_close", "price": 1.1010},
        {"timestamp": 1_700_000_060, "symbol": "EURUSD", "type": "bar_close", "price": 1.1015},
        {"timestamp": 1_700_000_120, "symbol": "EURUSD", "type": "bar_close", "price": 1.1012},
    ]
    same_run = list(baseline)
    drifted_run = [
        {"timestamp": 1_700_000_000, "symbol": "EURUSD", "type": "bar_close", "price": 1.1010},
        {"timestamp": 1_700_000_060, "symbol": "EURUSD", "type": "bar_close", "price": 1.1016},
        {"timestamp": 1_700_000_120, "symbol": "EURUSD", "type": "bar_close", "price": 1.1012},
    ]

    print("baseline fingerprint:", replay_fingerprint(baseline))
    print("same_run fingerprint:", replay_fingerprint(same_run))
    print("drifted_run fingerprint:", replay_fingerprint(drifted_run))

    ok_same, msg_same = compare_replay_runs(baseline, same_run)
    print("same run:", ok_same, "-", msg_same)

    ok_drift, msg_drift = compare_replay_runs(baseline, drifted_run)
    print("drifted run:", ok_drift, "-", msg_drift)


if __name__ == "__main__":
    main()
