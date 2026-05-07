"""Snapshot-based reporting helpers for the risk engine."""

from __future__ import annotations

_EXPORT_MODULES = {
    "RiskReportBuilder": "risk_report",
    "build_replay_report": "replay_report_builder",
    "build_risk_snapshot_report": "risk_report_builder",
    "build_scenario_report": "scenario_report_builder",
    "render_replay_report_markdown": "markdown_report",
    "render_risk_report_markdown": "markdown_report",
    "render_scenario_report_markdown": "markdown_report",
    "save_json_report": "json_export",
    "save_markdown_report": "json_export",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
