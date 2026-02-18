"""Integration tests for PositionBook reconciliation hooks via hqt_engine.sim."""

from __future__ import annotations

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


def _build_fill(symbol: str, is_buy: bool, volume: float, price: float):
    fill = sim.FillEvent()
    fill.symbol = symbol
    fill.is_buy = is_buy
    fill.volume = volume
    fill.price = price
    return fill


def test_periodic_reconcile_ok_when_snapshots_match():
    book = sim.PositionBook(sim.PositionMode.Netting)
    book.apply_fill(_build_fill("EURUSD", True, 1.0, 1.1000))

    account = sim.AccountInfoData()
    account.balance = 10000.0
    account.equity = 10000.0
    account.margin = 0.0
    book.apply_account_snapshot(account)

    report = book.periodic_reconcile(book.snapshot_positions(), book.snapshot_account())
    assert report.ok is True
    assert report.trigger == "periodic"
    assert report.position_mismatch_count == 0
    assert report.account_mismatch_count == 0


def test_reconnect_reconcile_reports_mismatch():
    book = sim.PositionBook(sim.PositionMode.Hedging)
    book.apply_fill(_build_fill("EURUSD", True, 1.0, 1.1000))
    book.apply_fill(_build_fill("EURUSD", False, 0.5, 1.1005))

    broker_positions = book.snapshot_positions()
    broker_positions["EURUSD"].net_volume = 0.9  # induce mismatch

    report = book.reconnect_reconcile(broker_positions, book.snapshot_account())
    assert report.ok is False
    assert report.trigger == "reconnect"
    assert report.position_mismatch_count > 0
    assert len(report.issues) > 0

