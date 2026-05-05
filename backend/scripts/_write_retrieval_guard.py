"""Validate that the retrieval guard module exists.

The canonical implementation lives in backend/agents/runtime/retrieval_guard.py.
This script is kept only for older developer workflows that invoked the writer
directly.
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RETRIEVAL_GUARD = ROOT / "backend" / "agents" / "runtime" / "retrieval_guard.py"


def main() -> None:
    if not RETRIEVAL_GUARD.exists():
        raise FileNotFoundError(RETRIEVAL_GUARD)
    print(f"retrieval_guard.py already exists at {RETRIEVAL_GUARD}")


if __name__ == "__main__":
    main()
