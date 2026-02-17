"""Integration tests for DataValidator DQ alerting/remediation outputs (IP-10)."""

from __future__ import annotations

import pandas as pd

from apps.utils.data_validator import DataValidator


def test_data_quality_alerts_include_missing_duplicate_and_out_of_order_with_remediation():
    df = pd.DataFrame(
        {
            "Datetime": pd.to_datetime(
                [
                    "2026-02-17 00:00:00",
                    "2026-02-17 02:00:00",
                    "2026-02-17 01:00:00",
                    "2026-02-17 01:00:00",
                ]
            ),
            "Open": [1.1000, 1.1005, 1.1002, 1.1002],
            "High": [1.1008, 1.1009, 1.1007, 1.1007],
            "Low": [1.0995, 1.1000, 1.0998, 1.0998],
            "Close": [1.1004, 1.1006, 1.1001, 1.1001],
            "Volume": [10.0, 0.0, 11.0, 12.0],
            "Spread": [0.0002, 0.0002, 0.0002, 0.0002],
        }
    )

    validator = DataValidator()
    results = validator.validate(
        df,
        checks=[
            "monotonic_timestamps",
            "normalized_schema",
            "missing_timestamps",
            "duplicates",
            "zero_volume",
        ],
        expected_frequency="1h",
        start_date=pd.Timestamp("2026-02-17 00:00:00"),
        end_date=pd.Timestamp("2026-02-17 03:00:00"),
    )

    issue_types = {issue["type"] for issue in results["issues_found"]}
    assert "monotonic_timestamps" in issue_types
    assert "duplicates" in issue_types
    assert "missing_timestamps" in issue_types
    assert "zero_volume" in issue_types

    for issue in results["issues_found"]:
        assert "severity" in issue
        assert "remediation_action" in issue
        assert "remediation_required" in issue

    remediation = results["summary"]["remediation"]
    assert remediation["severity_counts"]["high"] >= 1
    assert remediation["needs_immediate_action"] is True


def test_spread_widening_alert_has_remediation_metadata():
    idx = pd.date_range("2026-02-17 00:00:00", periods=8, freq="h")
    df = pd.DataFrame(
        {
            "open": [1.1000] * 8,
            "high": [1.1010] * 8,
            "low": [1.0990] * 8,
            "close": [1.1005] * 8,
            "volume": [10.0] * 8,
            "spread": [0.0002, 0.0002, 0.0002, 0.0002, 0.0002, 0.0002, 0.0002, 0.0200],
        },
        index=idx,
    )

    validator = DataValidator()
    results = validator.validate(df, checks=["spread"])
    spread_issues = [
        issue
        for issue in results["issues_found"]
        if issue.get("type") == "spread_anomaly" and issue.get("issue") == "wide_spread"
    ]

    assert spread_issues
    assert spread_issues[0]["severity"] in {"medium", "high"}
    assert spread_issues[0]["remediation_action"] == "flag_wide_spread_regime"
