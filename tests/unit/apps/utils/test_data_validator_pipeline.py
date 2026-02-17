"""Pipeline tests for DataValidator comprehensive validation."""

from __future__ import annotations

import pandas as pd

from apps.utils.data_validator import DataValidator


def test_validate_runs_schema_normalization_first() -> None:
    df = pd.DataFrame(
        {
            "Datetime": pd.date_range("2024-01-01", periods=3, freq="h"),
            "Open": [1.0, 1.1, 1.2],
            "High": [1.2, 1.3, 1.4],
            "Low": [0.9, 1.0, 1.1],
            "Close": [1.1, 1.2, 1.3],
            "Volume": [10, 12, 15],
            "Spread": [0.0001, 0.0001, 0.0001],
        }
    )

    validator = DataValidator()
    result = validator.validate(df, checks=["normalized_schema"])

    assert "normalized_schema" in result["checks_performed"]
    assert result["summary"]["normalized_schema"]["valid"] is True
    assert result["summary"]["is_valid"] is True
    assert result["summary"]["total_issues"] == 0


def test_validate_reports_schema_issue_when_not_normalizable() -> None:
    df = pd.DataFrame(
        {
            "Open": [1.0, 1.1],
            "High": [1.2, 1.3],
            "Low": [0.9, 1.0],
            "Close": [1.1, 1.2],
            # Missing datetime/time and volume/spread.
        }
    )

    validator = DataValidator()
    result = validator.validate(df, checks=["normalized_schema"])

    assert "normalized_schema" in result["checks_performed"]
    assert result["summary"]["normalized_schema"]["valid"] is False
    assert result["summary"]["is_valid"] is False
    assert result["summary"]["total_issues"] == 1
    assert result["issues_found"][0]["type"] == "schema_validation"


def test_validate_reports_non_monotonic_timestamps() -> None:
    # Deliberately out of order at position 2.
    df = pd.DataFrame(
        {
            "Datetime": pd.to_datetime(
                ["2024-01-01 00:00:00", "2024-01-01 02:00:00", "2024-01-01 01:00:00"]
            ),
            "Open": [1.0, 1.1, 1.2],
            "High": [1.2, 1.3, 1.4],
            "Low": [0.9, 1.0, 1.1],
            "Close": [1.1, 1.2, 1.3],
            "Volume": [10, 12, 15],
            "Spread": [0.0001, 0.0001, 0.0001],
        }
    )

    validator = DataValidator()
    result = validator.validate(df, checks=["monotonic_timestamps", "normalized_schema"])

    assert "monotonic_timestamps" in result["checks_performed"]
    assert result["summary"]["monotonic_timestamps"]["is_monotonic"] is False
    assert result["summary"]["monotonic_timestamps"]["disorder_count"] == 1
    assert any(issue["type"] == "monotonic_timestamps" for issue in result["issues_found"])


def test_validate_accepts_monotonic_timestamps() -> None:
    df = pd.DataFrame(
        {
            "Datetime": pd.to_datetime(
                ["2024-01-01 00:00:00", "2024-01-01 01:00:00", "2024-01-01 02:00:00"]
            ),
            "Open": [1.0, 1.1, 1.2],
            "High": [1.2, 1.3, 1.4],
            "Low": [0.9, 1.0, 1.1],
            "Close": [1.1, 1.2, 1.3],
            "Volume": [10, 12, 15],
            "Spread": [0.0001, 0.0001, 0.0001],
        }
    )

    validator = DataValidator()
    result = validator.validate(df, checks=["monotonic_timestamps"])

    assert result["summary"]["monotonic_timestamps"]["is_monotonic"] is True
    assert result["summary"]["monotonic_timestamps"]["disorder_count"] == 0
