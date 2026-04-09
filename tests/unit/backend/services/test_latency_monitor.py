from __future__ import annotations

from backend.services.performance import LatencyBudgetMonitor, LatencySample


def test_latency_budget_monitor_emits_alerts_only_for_budget_breaches() -> None:
    monitor = LatencyBudgetMonitor(threshold_ms=250)

    alerts = monitor.evaluate_many(
        (
            LatencySample(operation="risk_request", latency_ms=180),
            LatencySample(operation="mt5_send", latency_ms=320),
        )
    )

    assert len(alerts) == 1
    assert alerts[0].operation == "mt5_send"
    assert alerts[0].threshold_ms == 250
    assert alerts[0].observed_latency_ms == 320
