"""Usage example for IP-12 schema registry contracts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.contracts.schema_registry import create_default_schema_registry


def main() -> None:
    registry = create_default_schema_registry()
    print("registered event.tick versions:", registry.list_versions(name="event.tick"))

    ok, msg = registry.validate(
        name="event.tick",
        version="1.0",
        payload={
            "provider": "mt5_ea",
            "schema_version": "1.0",
            "symbol": "EURUSD",
            "timestamp": "2026-02-17T12:00:00Z",
            "bid": 1.1000,
            "ask": 1.1002,
            "volume": 100.0,
        },
    )
    print("tick validation:", ok, msg)

    ok2, msg2 = registry.validate(
        name="storage.run_manifest",
        version="1.0",
        payload={
            "schema_version": "1.0",
            "run_id": "run-001",
            "strategy_name": "TrendFollowing",
            "strategy_version": "1.2.0",
            "started_at": "2026-02-17T12:00:00Z",
            "environment": "backtest",
            "symbols": ["EURUSD", "GBPUSD"],
            "timeframe": "M15",
            "config_hash": "abc123",
            "seed": 42,
        },
    )
    print("manifest validation:", ok2, msg2)


if __name__ == "__main__":
    main()
