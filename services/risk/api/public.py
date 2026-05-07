"""Lightweight public facades for the risk service."""

from __future__ import annotations


class PortfolioStateBuilder:
    """Lazy public facade for the portfolio state builder."""

    def __new__(cls, *args, **kwargs):
        from services.risk.portfolio.state_builder import PortfolioStateEngine

        return PortfolioStateEngine(*args, **kwargs)


class RiskSnapshotBuilder:
    """Lazy public facade for the risk snapshot builder."""

    def __new__(cls, *args, **kwargs):
        from services.risk.portfolio.snapshot_builder import RiskSnapshotEngine

        return RiskSnapshotEngine(*args, **kwargs)


class RiskReportBuilder:
    """Lazy public facade for current risk reports."""

    def __new__(cls, *args, **kwargs):
        from services.risk.reports.risk_report import RiskReportBuilder as _RiskReportBuilder

        return _RiskReportBuilder(*args, **kwargs)


__all__ = ["PortfolioStateBuilder", "RiskReportBuilder", "RiskSnapshotBuilder"]
