"""E2E-style reconciliation mismatch blocking tests via hqt_engine.sim."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_build_dir = Path(__file__).resolve().parents[2] / "build" / "bridge" / "Release"
if _build_dir.exists():
    sys.path.insert(0, str(_build_dir))

try:
    from hqt_engine import sim

    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ bridge not available")


def test_major_mismatch_blocks_in_auto_policy(tmp_path):
    book = sim.PositionBook(sim.PositionMode.Netting)

    local = sim.AccountInfo(10000.0, "USD", 100)
    book.apply_account_snapshot(local)

    broker_positions = {}
    pa = sim.PositionAggregate()
    pa.net_volume = 1.0
    pa.long_volume = 1.0
    broker_positions["EURUSD"] = pa

    pb = sim.PositionAggregate()
    pb.net_volume = -1.0
    pb.short_volume = 1.0
    broker_positions["GBPUSD"] = pb

    broker = sim.AccountInfo(9800.0, "USD", 100)

    report = book.reconnect_reconcile(broker_positions, broker)
    decision = book.evaluate_reconciliation(report, sim.ReconcilePolicy.Auto, 2)

    assert report.ok is False
    assert decision.allow_new_orders is False
    assert decision.requires_manual_resolution is True

    out_path = tmp_path / "reconcile_discrepancy_report.json"
    assert book.write_incident_report(str(out_path), report, decision) is True

    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["ok"] is False
    assert payload["decision"]["allow_new_orders"] is False
    assert isinstance(payload["issues"], list)
    assert len(payload["issues"]) > 0


def test_manual_policy_blocks_on_any_mismatch():
    book = sim.PositionBook(sim.PositionMode.Netting)

    broker_positions = {}
    pa = sim.PositionAggregate()
    pa.net_volume = 0.1
    broker_positions["EURUSD"] = pa

    broker = sim.AccountInfo()
    report = book.periodic_reconcile(broker_positions, broker)
    decision = book.evaluate_reconciliation(report, sim.ReconcilePolicy.Manual, 10)

    assert report.ok is False
    assert decision.allow_new_orders is False
    assert decision.requires_manual_resolution is True


