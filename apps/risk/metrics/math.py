"""Shared metric math derived from the existing governor formulas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from apps.risk.limits import RiskLimits
from apps.risk.models import PortfolioState


def state_positions_map(state: PortfolioState) -> Dict[str, float]:
    """Return the signed position map for the current portfolio state."""
    return state.position_map


def state_symbol_list(state: PortfolioState) -> List[str]:
    """Return active symbols in deterministic order."""
    return list(state.position_map.keys())


def build_returns_df(
    state: PortfolioState,
    symbols: Optional[List[str]] = None,
    exclude_current_bar: bool = True,
) -> pd.DataFrame:
    """Build a log-returns dataframe from canonical market slices."""
    active = symbols or state_symbol_list(state)
    cols: Dict[str, pd.Series] = {}
    for symbol in active:
        market = state.markets.get(symbol)
        if market is None or market.bars.empty:
            continue
        bars = market.bars
        if exclude_current_bar and len(bars) > 1:
            bars = bars.iloc[:-1]
        close_col = "Close" if "Close" in bars.columns else "close"
        if close_col not in bars.columns:
            continue
        px = bars[close_col].astype(float)
        cols[symbol] = np.log(px / px.shift(1))
    if not cols:
        return pd.DataFrame()
    return pd.DataFrame(cols).dropna(how="all")


def estimate_covariance(
    returns_df: pd.DataFrame,
    symbols: List[str],
    limits: RiskLimits,
) -> np.ndarray:
    """Estimate covariance using the same rolling logic as the governor."""
    if returns_df.empty:
        return np.zeros((len(symbols), len(symbols)), dtype=float)

    r = returns_df[symbols].dropna()
    if r.empty:
        return np.zeros((len(symbols), len(symbols)), dtype=float)

    vol = r.rolling(limits.vol_lookback).std().iloc[-1].values
    vol = np.nan_to_num(vol, nan=0.0)

    rolling_corr = r.rolling(limits.corr_lookback).corr()
    if rolling_corr.empty:
        corr_mat = np.eye(len(symbols), dtype=float)
    else:
        last_ts = rolling_corr.index.get_level_values(0).unique()[-1]
        corr_mat = (
            rolling_corr.loc[last_ts].reindex(index=symbols, columns=symbols).values
        )
        corr_mat = np.nan_to_num(corr_mat, nan=0.0)
        np.fill_diagonal(corr_mat, 1.0)
        corr_mat = apply_corr_floors(corr_mat, limits)

    return np.outer(vol, vol) * corr_mat


def apply_corr_floors(corr_mat: np.ndarray, limits: RiskLimits) -> np.ndarray:
    """Apply configured pairwise correlation floors."""
    n = corr_mat.shape[0]
    out = corr_mat.copy()

    floor = (
        limits.stressed_corr_floor
        if limits.use_stressed_corr
        else limits.min_pair_corr
    )
    floor = max(limits.min_pair_corr, floor)

    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            out[i, j] = max(out[i, j], floor)

    out = np.clip(out, -1.0, 1.0)
    np.fill_diagonal(out, 1.0)
    return out


def symbol_notional_value(
    state: PortfolioState,
    symbol: str,
    lots: float,
    exclude_current_bar: bool = False,
) -> float:
    """Estimate symbol notional value from canonical state."""
    market = state.markets.get(symbol)
    spec = state.symbols.get(symbol)
    if market is None or spec is None:
        return 0.0

    bars = market.bars
    if exclude_current_bar and len(bars) > 1:
        bars = bars.iloc[:-1]
    close_col = "Close" if "Close" in bars.columns else "close"
    price = None
    if close_col in bars.columns and not bars.empty:
        price = float(bars[close_col].iloc[-1])
    if price is None:
        return 0.0

    if spec.contract_size and spec.contract_size > 0:
        return float(lots * spec.contract_size * price)

    if (
        spec.tick_value
        and spec.tick_value > 0
        and spec.tick_size
        and spec.tick_size > 0
    ):
        value_per_price_unit = spec.tick_value / spec.tick_size
        return float(lots * value_per_price_unit * price)

    return 0.0


def build_weights_from_state(
    state: PortfolioState,
    symbols: Optional[List[str]] = None,
    exclude_current_bar: bool = False,
) -> np.ndarray:
    """Build absolute notional weights for active symbols."""
    active = symbols or state_symbol_list(state)
    notionals = [
        abs(
            symbol_notional_value(
                state,
                symbol,
                float(state.position_map.get(symbol, 0.0)),
                exclude_current_bar=exclude_current_bar,
            )
        )
        for symbol in active
    ]
    total = float(np.sum(notionals))
    if total <= 0:
        return np.zeros(len(active), dtype=float)
    return np.array([n / total for n in notionals], dtype=float)


def compute_risk_contributions_pct(
    weights: np.ndarray,
    cov: np.ndarray,
    symbols: List[str],
) -> Dict[str, float]:
    """Compute percentage contribution to total portfolio variance."""
    port_var = float(weights.T @ cov @ weights)
    if port_var <= 0:
        return dict.fromkeys(symbols, 0.0)
    mrc = cov @ weights
    rc = weights * mrc
    rc_pct = rc / port_var
    return {symbols[i]: float(rc_pct[i]) for i in range(len(symbols))}


def estimate_margin_used(state: PortfolioState) -> Optional[float]:
    """Return current margin used from the canonical account state when available."""
    return state.account.margin_used


def compute_portfolio_var_es(
    state: PortfolioState,
    limits: Optional[RiskLimits] = None,
) -> Tuple[float, float, Optional[Dict[str, float]], Dict[str, Any]]:
    """Compute current portfolio VaR/ES and shared risk math artifacts."""
    eff = limits or state.limits or RiskLimits()
    symbols = state_symbol_list(state)
    if not symbols:
        return 0.0, 0.0, {}, {
            "weights": np.zeros(0, dtype=float),
            "covariance": np.zeros((0, 0), dtype=float),
            "returns_df": pd.DataFrame(),
            "portfolio_notional": 0.0,
            "portfolio_std": 0.0,
            "symbols": [],
        }

    returns_df = build_returns_df(state, symbols)
    need = max(eff.vol_lookback, eff.corr_lookback)
    if returns_df.empty or returns_df.dropna().shape[0] < need:
        return float("inf"), float("inf"), None, {
            "weights": np.zeros(len(symbols), dtype=float),
            "covariance": np.zeros((len(symbols), len(symbols)), dtype=float),
            "returns_df": returns_df,
            "portfolio_notional": 0.0,
            "portfolio_std": 0.0,
            "symbols": symbols,
        }

    cov = estimate_covariance(returns_df, symbols, eff)
    weights = build_weights_from_state(state, symbols, exclude_current_bar=True)
    port_var = float(weights.T @ cov @ weights)
    port_std = float(np.sqrt(max(port_var, 0.0)))
    portfolio_notional = float(
        sum(
            abs(
                symbol_notional_value(
                    state,
                    symbol,
                    state.position_map[symbol],
                    exclude_current_bar=True,
                )
            )
            for symbol in symbols
        )
    )
    if portfolio_notional <= 0 or port_std <= 0:
        return float("inf"), float("inf"), None, {
            "weights": weights,
            "covariance": cov,
            "returns_df": returns_df,
            "portfolio_notional": portfolio_notional,
            "portfolio_std": port_std,
            "symbols": symbols,
        }

    z = stats.norm.ppf(eff.confidence_level)
    t = np.sqrt(eff.time_horizon_days)
    var_dollar = z * port_std * t * portfolio_notional
    alpha = eff.confidence_level
    phi = stats.norm.pdf(z)
    es_dollar = (phi / (1.0 - alpha)) * port_std * t * portfolio_notional
    rc_map = compute_risk_contributions_pct(weights, cov, symbols)

    return float(var_dollar), float(es_dollar), rc_map, {
        "weights": weights,
        "covariance": cov,
        "returns_df": returns_df,
        "portfolio_notional": portfolio_notional,
        "portfolio_std": port_std,
        "symbols": symbols,
    }


def extract_currency_exposure(state: PortfolioState) -> Dict[str, float]:
    """Build a simple currency exposure map from symbol metadata or naming conventions."""
    exposure: Dict[str, float] = {}

    for position in state.positions:
        symbol = position.symbol
        spec = state.symbols.get(symbol)
        notional = symbol_notional_value(state, symbol, position.lots)
        if notional == 0.0:
            continue

        base = (spec.currency_base if spec else None) or _symbol_base_currency(symbol)
        quote = (spec.currency_profit if spec else None) or _symbol_quote_currency(symbol)

        if base:
            exposure[base] = exposure.get(base, 0.0) + notional
        if quote:
            exposure[quote] = exposure.get(quote, 0.0) - notional

    return exposure


def _symbol_base_currency(symbol: str) -> Optional[str]:
    token = str(symbol).upper()
    if len(token) >= 6 and token[:6].isalpha():
        return token[:3]
    return None


def _symbol_quote_currency(symbol: str) -> Optional[str]:
    token = str(symbol).upper()
    if len(token) >= 6 and token[:6].isalpha():
        return token[3:6]
    return None
