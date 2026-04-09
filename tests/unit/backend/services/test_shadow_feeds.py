from __future__ import annotations

from datetime import datetime, timezone

from backend.services.risk import AccountSnapshot, MarketSnapshot, PortfolioSnapshot
from backend.services.shadow import build_shadow_data_feed


def test_build_shadow_data_feed_packages_live_shaped_snapshots() -> None:
    observed_at = datetime(2026, 4, 9, 10, 0, tzinfo=timezone.utc)
    account_snapshot = AccountSnapshot.from_policy(
        snapshot_id="acct_001",
        account_id="account_001",
        observed_at=observed_at,
        balance=10000.0,
        equity=10100.0,
        free_margin=7500.0,
        margin_used=2600.0,
        currency="USD",
    )
    portfolio_snapshot = PortfolioSnapshot.from_policy(
        snapshot_id="port_001",
        portfolio_id="portfolio_001",
        observed_at=observed_at,
        open_position_count=2,
        gross_exposure=150000.0,
        net_exposure=25000.0,
        symbols=("EURUSD", "GBPUSD"),
    )
    market_snapshot = MarketSnapshot.from_policy(
        snapshot_id="mkt_001",
        symbol="EURUSD",
        snapshot_type="best_bid_ask_tick",
        observed_at=observed_at,
        best_bid=1.1,
        best_ask=1.1002,
        spread_points=2.0,
        tradable=True,
    )

    feed = build_shadow_data_feed(
        account_snapshot=account_snapshot,
        portfolio_snapshot=portfolio_snapshot,
        market_snapshot=market_snapshot,
    )

    assert feed.environment == "shadow"
    assert feed.account_snapshot_ref == "acct_001"
    assert feed.portfolio_snapshot_ref == "port_001"
    assert feed.market_snapshot_ref == "mkt_001"
    assert feed.payload["account"]["account_id"] == "account_001"
    assert feed.payload["portfolio"]["symbols"] == ["EURUSD", "GBPUSD"]
    assert feed.payload["market"]["symbol"] == "EURUSD"
