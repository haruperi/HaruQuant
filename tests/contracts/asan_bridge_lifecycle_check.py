"""ASan lifecycle stress check for hqt_engine bridge.

Run this under an ASan-instrumented build with:
  ASAN_OPTIONS=detect_leaks=1:halt_on_error=1
"""

from __future__ import annotations

import sys
from pathlib import Path


def _add_bridge_to_path() -> None:
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "build" / "bridge",
        root / "build" / "bridge" / "Release",
    ]
    for c in candidates:
        if c.exists():
            sys.path.insert(0, str(c))


def main() -> int:
    _add_bridge_to_path()
    try:
        import hqt_engine
    except Exception as exc:  # pragma: no cover
        print(f"SKIP: hqt_engine import failed ({exc})")
        return 0

    loops = 2000
    for _ in range(loops):
        ok = hqt_engine.initialize()
        if ok is not True:
            raise RuntimeError("initialize() returned false")
        health = hqt_engine.health_check()
        if not isinstance(health, dict) or not health.get("ok", False):
            raise RuntimeError("health_check() failed")
        if hqt_engine.teardown() is not True:
            raise RuntimeError("teardown() returned false")

    print(f"ASan lifecycle stress check passed ({loops} initialize/teardown cycles).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
