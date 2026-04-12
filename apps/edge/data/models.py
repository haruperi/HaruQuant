"""Models for Edge Lab dataset validation, cleaning, and enrichment."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class CanonicalOHLCVSSchema:
    """Canonical analysis-ready OHLCVS schema."""

    open: str = "Open"
    high: str = "High"
    low: str = "Low"
    close: str = "Close"
    volume: str = "Volume"
    spread: str = "Spread"

    @property
    def price_columns(self) -> List[str]:
        return [self.open, self.high, self.low, self.close]

    @property
    def required_columns(self) -> List[str]:
        return [self.open, self.high, self.low, self.close, self.volume, self.spread]


@dataclass
class DatasetIssue:
    """A single validation or cleaning issue."""

    code: str
    severity: str
    message: str
    count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CleaningAction:
    """A single cleaning action applied to the dataset."""

    action: str
    count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataQualityReportModel:
    """Validation and cleaning report with warning/fatal separation."""

    checks_performed: List[str] = field(default_factory=list)
    warnings: List[DatasetIssue] = field(default_factory=list)
    fatal_errors: List[DatasetIssue] = field(default_factory=list)
    cleaning_actions: List[CleaningAction] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        return len(self.fatal_errors) == 0

    def add_issue(self, issue: DatasetIssue) -> None:
        if issue.severity == "fatal":
            self.fatal_errors.append(issue)
        else:
            self.warnings.append(issue)

    def add_check(self, name: str) -> None:
        if name not in self.checks_performed:
            self.checks_performed.append(name)

    def add_action(self, action: CleaningAction) -> None:
        self.cleaning_actions.append(action)


@dataclass
class PreparedDataset:
    """Prepared dataset and its data quality report."""

    data: pd.DataFrame
    report: DataQualityReportModel
    schema: CanonicalOHLCVSSchema = field(default_factory=CanonicalOHLCVSSchema)
