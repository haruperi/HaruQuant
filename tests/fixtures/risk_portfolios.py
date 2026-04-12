from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.services.risk_engine import PortfolioStateEngine, RiskLimits


def _bars(
    *,
    periods: int = 160,
    start: str = "2024-01-01",
    scale: float = 1.0,
    wave: float = 0.00012,
    drift: float = 0.00030,
    spread: float = 1.0,
) -> pd.DataFrame:
    idx = pd.date_range(start, periods=periods, freq="h")
    base = pd.Series(range(periods), index=idx, dtype=float)
    close = 1.10 + (base * drift * scale) + ((base % 7) * wave * scale)
    return pd.DataFrame(
        {
            "Close": close,
            "Open": close - 0.0002,
            "High": close + 0.0005,
            "Low": close - 0.0005,
            "Volume": [100 + i for i in range(periods)],
            "Spread": [spread + (i % 3) for i in range(periods)],
        },
        index=idx,
    )


def _equity_curve(values: list[float]) -> pd.Series:
    return pd.Series(
        values,
        index=pd.date_range("2024-01-01", periods=len(values), freq="h"),
        dtype=float,
    )


@dataclass(frozen=True)
class RiskPortfolioCase:
    name: str
    state: object
    notes: str


def _build_state(
    *,
    account: dict,
    positions: list[dict],
    symbol_specs: dict,
    market_data: dict,
    limits: RiskLimits,
    symbol_to_cluster: dict,
    as_of: str = "2024-01-06T15:00:00",
    metadata: dict | None = None,
):
    return PortfolioStateEngine().build_state(
        account=account,
        positions=positions,
        symbol_specs=symbol_specs,
        market_data=market_data,
        limits=limits,
        symbol_to_cluster=symbol_to_cluster,
        timeframe="H1",
        as_of=as_of,
        metadata=dict(metadata or {}),
    )


def build_risk_portfolio_cases() -> dict[str, RiskPortfolioCase]:
    symbol_specs = {
        "EURUSD": {"trade_contract_size": 100000, "lots_step": 0.01, "volume_min": 0.01},
        "GBPUSD": {"trade_contract_size": 100000, "lots_step": 0.01, "volume_min": 0.01},
        "USDJPY": {"trade_contract_size": 100000, "lots_step": 0.01, "volume_min": 0.01},
        "XAUUSD": {"trade_contract_size": 100, "lots_step": 0.01, "volume_min": 0.01},
    }

    balanced = _build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 8800.0,
            "margin_used": 1200.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.10, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.08, "type": "BUY"},
            {"symbol": "USDJPY", "volume": 0.06, "type": "SELL"},
        ],
        symbol_specs=symbol_specs,
        market_data={
            "EURUSD": _bars(scale=1.0),
            "GBPUSD": _bars(scale=0.9),
            "USDJPY": _bars(scale=0.8),
            "XAUUSD": _bars(scale=1.8),
        },
        limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"},
        metadata={"equity_curve": _equity_curve([10000, 10030, 10020, 10010, 10025, 10035, 10040])},
    )

    concentrated = _build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 8200.0,
            "margin_used": 1800.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.55, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.04, "type": "BUY"},
        ],
        symbol_specs=symbol_specs,
        market_data={
            "EURUSD": _bars(scale=1.1),
            "GBPUSD": _bars(scale=1.05),
            "USDJPY": _bars(scale=0.9),
            "XAUUSD": _bars(scale=1.6),
        },
        limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, max_single_rc_frac=0.18, vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX"},
        metadata={"equity_curve": _equity_curve([10000, 10010, 9980, 9940, 9925, 9910, 9905])},
    )

    fragile = _build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 4600.0,
            "margin_used": 5400.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.70, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.55, "type": "BUY"},
            {"symbol": "XAUUSD", "volume": 0.35, "type": "BUY"},
        ],
        symbol_specs=symbol_specs,
        market_data={
            "EURUSD": _bars(scale=1.3, wave=0.00020, drift=0.00042),
            "GBPUSD": _bars(scale=1.35, wave=0.00022, drift=0.00044),
            "USDJPY": _bars(scale=0.9),
            "XAUUSD": _bars(scale=3.4, wave=0.0012, drift=0.0018, spread=4.0),
        },
        limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, max_margin_used_frac=0.45, max_single_rc_frac=0.18, vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "XAUUSD": "METALS"},
        metadata={"equity_curve": _equity_curve([10000, 9950, 9840, 9720, 9660, 9600, 9580])},
    )

    high_corr = _build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 7600.0,
            "margin_used": 2400.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.22, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.21, "type": "BUY"},
            {"symbol": "USDJPY", "volume": 0.18, "type": "SELL"},
        ],
        symbol_specs=symbol_specs,
        market_data={
            "EURUSD": _bars(scale=1.0, wave=0.00016, drift=0.00034),
            "GBPUSD": _bars(scale=1.0, wave=0.00016, drift=0.00034),
            "USDJPY": _bars(scale=1.0, wave=0.00016, drift=0.00034),
            "XAUUSD": _bars(scale=2.0),
        },
        limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, corr_lookback=50, vol_lookback=20),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "USDJPY": "FOREX"},
        metadata={"equity_curve": _equity_curve([10000, 10005, 9995, 9985, 9970, 9960, 9955])},
    )

    margin_stressed = _build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 1800.0,
            "margin_used": 8200.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.45, "type": "BUY"},
            {"symbol": "GBPUSD", "volume": 0.40, "type": "BUY"},
            {"symbol": "XAUUSD", "volume": 0.20, "type": "SELL"},
        ],
        symbol_specs=symbol_specs,
        market_data={
            "EURUSD": _bars(scale=1.1),
            "GBPUSD": _bars(scale=1.15),
            "USDJPY": _bars(scale=0.85),
            "XAUUSD": _bars(scale=2.8, spread=4.0),
        },
        limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, max_margin_used_frac=0.40, vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "GBPUSD": "FOREX", "XAUUSD": "METALS"},
        metadata={"equity_curve": _equity_curve([10000, 9980, 9955, 9920, 9880, 9855, 9840])},
    )

    volatility_expansion = _build_state(
        account={
            "equity": 10000.0,
            "balance": 10000.0,
            "free_margin": 7600.0,
            "margin_used": 2400.0,
            "currency": "USD",
        },
        positions=[
            {"symbol": "EURUSD", "volume": 0.20, "type": "BUY"},
            {"symbol": "XAUUSD", "volume": 0.18, "type": "BUY"},
        ],
        symbol_specs=symbol_specs,
        market_data={
            "EURUSD": _bars(scale=1.8, wave=0.00035, drift=0.00055),
            "GBPUSD": _bars(scale=1.4, wave=0.00022, drift=0.00040),
            "USDJPY": _bars(scale=1.2),
            "XAUUSD": _bars(scale=4.5, wave=0.0018, drift=0.0020, spread=5.0),
        },
        limits=RiskLimits(var_cap_frac=0.08, es_cap_frac=0.12, vol_lookback=20, corr_lookback=40),
        symbol_to_cluster={"EURUSD": "FOREX", "XAUUSD": "METALS"},
        metadata={"equity_curve": _equity_curve([10000, 10020, 9980, 9890, 9810, 9760, 9725])},
    )

    cases = {
        "balanced": RiskPortfolioCase("balanced", balanced, "Low-risk diversified portfolio."),
        "concentrated_single_currency": RiskPortfolioCase("concentrated_single_currency", concentrated, "Single-currency concentration."),
        "high_leverage_fragile": RiskPortfolioCase("high_leverage_fragile", fragile, "High leverage and fragility."),
        "high_correlation_clustered": RiskPortfolioCase("high_correlation_clustered", high_corr, "Highly correlated clustered FX book."),
        "margin_stressed": RiskPortfolioCase("margin_stressed", margin_stressed, "Margin utilization near hard cap."),
        "volatility_expansion": RiskPortfolioCase("volatility_expansion", volatility_expansion, "High volatility stress case."),
    }
    return cases
