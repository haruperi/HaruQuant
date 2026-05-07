"""Simulation artifact path helpers."""

from __future__ import annotations

from pathlib import Path


def artifact_root(run_id: str) -> str:
    return str(Path("backtests") / "runs" / run_id)


def result_package_paths(run_id: str) -> dict[str, str]:
    root = artifact_root(run_id)
    return {
        "artifact_root": root,
        "config_path": f"{root}/config.yaml",
        "trades_path": f"{root}/trades.parquet",
        "orders_path": f"{root}/orders.parquet",
        "deals_path": f"{root}/deals.parquet",
        "equity_curve_path": f"{root}/equity_curve.parquet",
        "metrics_path": f"{root}/metrics.json",
        "analytics_path": f"{root}/analytics.json",
        "report_path": f"{root}/report.md",
        "audit_path": f"{root}/audit.json",
        "manifest_path": f"{root}/manifest.json",
    }
