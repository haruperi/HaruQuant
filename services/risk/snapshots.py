"""Snapshot models with freshness metadata for the safety core."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from services.utils.logger import logger
from services.utils.time_utils import Clock, FreshnessWindow, SystemClock, evaluate_freshness
from backend_retiring.contracts.risk_assessment_request.model import FreshnessClass


MarketSnapshotType = Literal["best_bid_ask_tick", "spread_snapshot", "symbol_tradability_status"]
AccountSnapshotType = Literal["account_equity_free_margin_snapshot"]
PortfolioSnapshotType = Literal["open_positions_snapshot"]

MARKET_SNAPSHOT_TTL_POLICY: dict[MarketSnapshotType, tuple[FreshnessClass, int]] = {
    "best_bid_ask_tick": ("HOT", 2),
    "spread_snapshot": ("HOT", 2),
    "symbol_tradability_status": ("HOT", 5),
}
ACCOUNT_SNAPSHOT_TTL_POLICY: dict[AccountSnapshotType, tuple[FreshnessClass, int]] = {
    "account_equity_free_margin_snapshot": ("HOT", 5),
}
PORTFOLIO_SNAPSHOT_TTL_POLICY: dict[PortfolioSnapshotType, tuple[FreshnessClass, int]] = {
    "open_positions_snapshot": ("HOT", 5),
}


class MarketSnapshot(BaseModel):
    """Market input snapshot with embedded TTL metadata."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    snapshot_type: MarketSnapshotType
    observed_at: datetime
    freshness_class: FreshnessClass
    max_age_seconds: int = Field(gt=0)
    best_bid: float | None = None
    best_ask: float | None = None
    spread_points: float | None = None
    tradable: bool | None = None
    source: str = Field(default="market_data_feed", min_length=1)

    @computed_field
    @property
    def expires_at(self) -> datetime:
        return evaluate_freshness(
            self.observed_at,
            max_age_seconds=self.max_age_seconds,
            clock=SystemClock(),
        ).expires_at

    @classmethod
    def from_policy(
        cls,
        *,
        snapshot_id: str,
        symbol: str,
        snapshot_type: MarketSnapshotType,
        observed_at: datetime,
        best_bid: float | None = None,
        best_ask: float | None = None,
        spread_points: float | None = None,
        tradable: bool | None = None,
        source: str = "market_data_feed",
    ) -> "MarketSnapshot":
        freshness_class, max_age_seconds = MARKET_SNAPSHOT_TTL_POLICY[snapshot_type]
        return cls(
            snapshot_id=snapshot_id,
            symbol=symbol,
            snapshot_type=snapshot_type,
            observed_at=observed_at,
            freshness_class=freshness_class,
            max_age_seconds=max_age_seconds,
            best_bid=best_bid,
            best_ask=best_ask,
            spread_points=spread_points,
            tradable=tradable,
            source=source,
        )

    def evaluate(self, *, clock: Clock | None = None) -> FreshnessWindow:
        """Evaluate the snapshot against its declared TTL."""

        return evaluate_freshness(
            self.observed_at,
            max_age_seconds=self.max_age_seconds,
            clock=clock,
        )


class AccountSnapshot(BaseModel):
    """Account state snapshot with embedded TTL metadata."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(min_length=1)
    account_id: str = Field(min_length=1)
    snapshot_type: AccountSnapshotType = "account_equity_free_margin_snapshot"
    observed_at: datetime
    freshness_class: FreshnessClass
    max_age_seconds: int = Field(gt=0)
    balance: float
    equity: float
    free_margin: float
    margin_used: float
    currency: str = Field(min_length=1)

    @computed_field
    @property
    def expires_at(self) -> datetime:
        return evaluate_freshness(
            self.observed_at,
            max_age_seconds=self.max_age_seconds,
            clock=SystemClock(),
        ).expires_at

    @classmethod
    def from_policy(
        cls,
        *,
        snapshot_id: str,
        account_id: str,
        observed_at: datetime,
        balance: float,
        equity: float,
        free_margin: float,
        margin_used: float,
        currency: str,
    ) -> "AccountSnapshot":
        freshness_class, max_age_seconds = ACCOUNT_SNAPSHOT_TTL_POLICY[
            "account_equity_free_margin_snapshot"
        ]
        return cls(
            snapshot_id=snapshot_id,
            account_id=account_id,
            observed_at=observed_at,
            freshness_class=freshness_class,
            max_age_seconds=max_age_seconds,
            balance=balance,
            equity=equity,
            free_margin=free_margin,
            margin_used=margin_used,
            currency=currency,
        )

    def evaluate(self, *, clock: Clock | None = None) -> FreshnessWindow:
        """Evaluate the snapshot against its declared TTL."""

        return evaluate_freshness(
            self.observed_at,
            max_age_seconds=self.max_age_seconds,
            clock=clock,
        )


class PortfolioSnapshot(BaseModel):
    """Portfolio state snapshot with embedded TTL metadata."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(min_length=1)
    portfolio_id: str = Field(min_length=1)
    snapshot_type: PortfolioSnapshotType = "open_positions_snapshot"
    observed_at: datetime
    freshness_class: FreshnessClass
    max_age_seconds: int = Field(gt=0)
    open_position_count: int = Field(ge=0)
    gross_exposure: float = Field(ge=0.0)
    net_exposure: float
    symbols: tuple[str, ...] = ()

    @computed_field
    @property
    def expires_at(self) -> datetime:
        return evaluate_freshness(
            self.observed_at,
            max_age_seconds=self.max_age_seconds,
            clock=SystemClock(),
        ).expires_at

    @classmethod
    def from_policy(
        cls,
        *,
        snapshot_id: str,
        portfolio_id: str,
        observed_at: datetime,
        open_position_count: int,
        gross_exposure: float,
        net_exposure: float,
        symbols: tuple[str, ...] = (),
    ) -> "PortfolioSnapshot":
        freshness_class, max_age_seconds = PORTFOLIO_SNAPSHOT_TTL_POLICY[
            "open_positions_snapshot"
        ]
        return cls(
            snapshot_id=snapshot_id,
            portfolio_id=portfolio_id,
            observed_at=observed_at,
            freshness_class=freshness_class,
            max_age_seconds=max_age_seconds,
            open_position_count=open_position_count,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            symbols=symbols,
        )

    def evaluate(self, *, clock: Clock | None = None) -> FreshnessWindow:
        """Evaluate the snapshot against its declared TTL."""

        return evaluate_freshness(
            self.observed_at,
            max_age_seconds=self.max_age_seconds,
            clock=clock,
        )
