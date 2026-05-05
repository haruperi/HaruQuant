"""Shared metric math derived from the existing governance formulas."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from services.risk.limits import RiskLimits
from services.risk.models import PortfolioState


_FX_BRIDGE_CURRENCIES = ("USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD")


def _timeframe_hours(timeframe: str) -> float:
    mapping = {
        "M1": 1.0 / 60.0,
        "M5": 5.0 / 60.0,
        "M15": 15.0 / 60.0,
        "M30": 30.0 / 60.0,
        "H1": 1.0,
        "H4": 4.0,
        "D1": 24.0,
        "W1": 24.0 * 7.0,
    }
    return float(mapping.get(str(timeframe or "D1").upper(), 24.0))


def _risk_horizon_bar_count(state: PortfolioState, limits: RiskLimits) -> float:
    metadata = dict(state.metadata or {})
    horizon_unit = str(metadata.get("risk_horizon_unit", "days") or "days").lower()
    try:
        horizon_value = float(metadata.get("risk_horizon_value", limits.time_horizon_days) or limits.time_horizon_days)
    except (TypeError, ValueError):
        horizon_value = float(limits.time_horizon_days)
    horizon_value = max(horizon_value, 1.0)

    timeframe = str(metadata.get("timeframe", "D1") or "D1")
    bar_hours = max(_timeframe_hours(timeframe), 1.0 / 60.0)

    if horizon_unit == "bars":
        return horizon_value
    if horizon_unit == "hours":
        return max(horizon_value / bar_hours, 1.0)
    if horizon_unit == "days":
        return horizon_value
    return max(float(limits.time_horizon_days), 1.0)


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


def estimate_correlation_matrix(
    returns_df: pd.DataFrame,
    symbols: List[str],
    limits: RiskLimits,
) -> np.ndarray:
    """Estimate the latest rolling correlation matrix for active symbols."""
    if returns_df.empty:
        return np.eye(len(symbols), dtype=float)

    r = returns_df[symbols].dropna()
    if r.empty:
        return np.eye(len(symbols), dtype=float)

    rolling_corr = r.rolling(limits.corr_lookback).corr()
    if rolling_corr.empty:
        return np.eye(len(symbols), dtype=float)

    last_ts = rolling_corr.index.get_level_values(0).unique()[-1]
    corr_mat = rolling_corr.loc[last_ts].reindex(index=symbols, columns=symbols).values
    corr_mat = np.nan_to_num(corr_mat, nan=0.0)
    corr_mat = np.clip(corr_mat, -1.0, 1.0)
    np.fill_diagonal(corr_mat, 1.0)
    return corr_mat


def apply_corr_floors(corr_mat: np.ndarray, limits: RiskLimits) -> np.ndarray:
    """Apply correlation stress only when stressed covariance is requested."""
    out = corr_mat.copy()
    if limits.use_stressed_corr:
        floor = max(limits.min_pair_corr, limits.stressed_corr_floor)
        n = corr_mat.shape[0]
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
    """Estimate symbol notional value normalized to account currency."""
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
        raw_notional = float(lots * spec.contract_size * price)
        profit_currency = spec.currency_profit or _symbol_quote_currency(symbol)
        return _convert_value_to_account_currency(
            raw_notional,
            profit_currency,
            _state_account_currency(state),
            lambda pair: _market_price_for_symbol_state(
                state, pair, exclude_current_bar=exclude_current_bar
            ),
        )

    if (
        spec.tick_value
        and spec.tick_value > 0
        and spec.tick_size
        and spec.tick_size > 0
    ):
        value_per_price_unit = spec.tick_value / spec.tick_size
        raw_notional = float(lots * value_per_price_unit * price)
        profit_currency = spec.currency_profit or _symbol_quote_currency(symbol)
        return _convert_value_to_account_currency(
            raw_notional,
            profit_currency,
            _state_account_currency(state),
            lambda pair: _market_price_for_symbol_state(
                state, pair, exclude_current_bar=exclude_current_bar
            ),
        )

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


def build_signed_weights_from_state(
    state: PortfolioState,
    symbols: Optional[List[str]] = None,
    exclude_current_bar: bool = False,
) -> np.ndarray:
    """Build signed notional weights normalized by gross absolute notional."""
    active = symbols or state_symbol_list(state)
    signed_notionals = [
        symbol_notional_value(
            state,
            symbol,
            float(state.position_map.get(symbol, 0.0)),
            exclude_current_bar=exclude_current_bar,
        )
        for symbol in active
    ]
    total = float(np.sum([abs(float(notional)) for notional in signed_notionals]))
    if total <= 0:
        return np.zeros(len(active), dtype=float)
    return np.array([float(notional) / total for notional in signed_notionals], dtype=float)


def build_notional_vector(
    state: PortfolioState,
    symbols: Optional[List[str]] = None,
    exclude_current_bar: bool = False,
) -> np.ndarray:
    """Return absolute notional exposures for active symbols."""
    active = symbols or state_symbol_list(state)
    return np.array(
        [
            abs(
                symbol_notional_value(
                    state,
                    symbol,
                    float(state.position_map.get(symbol, 0.0)),
                    exclude_current_bar=exclude_current_bar,
                )
            )
            for symbol in active
        ],
        dtype=float,
    )


def compute_symbol_volatility_state(
    returns_df: pd.DataFrame,
    symbols: List[str],
    limits: RiskLimits,
) -> Dict[str, float]:
    """Return latest rolling realized volatility per symbol."""
    if returns_df.empty:
        return dict.fromkeys(symbols, 0.0)

    r = returns_df[symbols].dropna()
    if r.empty:
        return dict.fromkeys(symbols, 0.0)

    vol = r.rolling(limits.vol_lookback).std().iloc[-1]
    if isinstance(vol, pd.Series):
        return {symbol: float(vol.get(symbol, 0.0) or 0.0) for symbol in symbols}
    return dict.fromkeys(symbols, 0.0)


def average_off_diagonal(corr_mat: np.ndarray) -> float:
    """Return the mean off-diagonal correlation for a square matrix."""
    if corr_mat.size == 0 or corr_mat.shape[0] <= 1:
        return 0.0
    mask = ~np.eye(corr_mat.shape[0], dtype=bool)
    values = corr_mat[mask]
    if values.size == 0:
        return 0.0
    return float(np.mean(values))


def max_off_diagonal(corr_mat: np.ndarray) -> float:
    """Return the maximum off-diagonal correlation for a square matrix."""
    if corr_mat.size == 0 or corr_mat.shape[0] <= 1:
        return 0.0
    mask = ~np.eye(corr_mat.shape[0], dtype=bool)
    values = corr_mat[mask]
    if values.size == 0:
        return 0.0
    return float(np.max(values))


def compute_diversification_ratio(
    weights: np.ndarray,
    cov: np.ndarray,
) -> float:
    """Return the diversification ratio for the current portfolio."""
    if weights.size == 0 or cov.size == 0:
        return 0.0
    sigma = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    numerator = float(weights @ sigma)
    denominator = float(np.sqrt(max(weights.T @ cov @ weights, 0.0)))
    if denominator <= 0.0:
        return 0.0
    return numerator / denominator


def compute_effective_independent_bets(
    corr_mat: np.ndarray,
) -> float:
    """Estimate effective independent bets from correlation eigenvalues."""
    if corr_mat.size == 0:
        return 0.0
    try:
        eigenvalues = np.linalg.eigvalsh(corr_mat)
    except np.linalg.LinAlgError:
        return 0.0
    eigenvalues = np.clip(eigenvalues, 0.0, None)
    total = float(np.sum(eigenvalues))
    denom = float(np.sum(np.square(eigenvalues)))
    if total <= 0.0 or denom <= 0.0:
        return 0.0
    return (total * total) / denom


def compute_hidden_overlap_score(
    weights: np.ndarray,
    corr_mat: np.ndarray,
) -> float:
    """Estimate hidden overlap from weighted pairwise correlation."""
    if weights.size <= 1 or corr_mat.size == 0:
        return 0.0
    overlap = 0.0
    for i in range(len(weights)):
        for j in range(i + 1, len(weights)):
            overlap += float(weights[i] * weights[j] * max(corr_mat[i, j], 0.0))
    return float(min(max(overlap * 2.0, 0.0), 1.0))


def compute_cluster_exposure_breakdown(
    state: PortfolioState,
    symbols: Optional[List[str]] = None,
    exclude_current_bar: bool = False,
) -> Dict[str, float]:
    """Aggregate gross notional exposure by cluster."""
    active = symbols or state_symbol_list(state)
    cluster_gross: Dict[str, float] = {}
    for symbol in active:
        memberships = _cluster_memberships_for_symbol(
            symbol,
            getattr(state, "symbol_to_clusters", {}),
            getattr(state, "symbol_to_cluster", {}),
        )
        position_lots = float(state.position_map.get(symbol, 0.0))
        if not memberships or abs(position_lots) <= 0.0:
            continue
        gross_value = abs(
            symbol_notional_value(
                state,
                symbol,
                position_lots,
                exclude_current_bar=exclude_current_bar,
            )
        )
        for cluster in memberships:
            cluster_gross[cluster] = cluster_gross.get(cluster, 0.0) + gross_value
    return cluster_gross


def compute_cluster_correlation_summary(
    symbols: List[str],
    corr_mat: np.ndarray,
    symbol_to_cluster: Dict[str, Any],
) -> Dict[str, Dict[str, float]]:
    """Summarize average and max intra-cluster correlation."""
    summary: Dict[str, Dict[str, float]] = {}
    cluster_to_indices: Dict[str, List[int]] = {}
    for idx, symbol in enumerate(symbols):
        memberships = _cluster_memberships_for_symbol(symbol, {}, symbol_to_cluster)
        if not memberships:
            continue
        for cluster in memberships:
            cluster_to_indices.setdefault(cluster, []).append(idx)

    for cluster, indices in cluster_to_indices.items():
        if len(indices) <= 1:
            summary[cluster] = {"avg_corr": 0.0, "max_corr": 0.0, "symbol_count": float(len(indices))}
            continue
        values: List[float] = []
        for i_pos, i in enumerate(indices):
            for j in indices[i_pos + 1 :]:
                values.append(float(corr_mat[i, j]))
        summary[cluster] = {
            "avg_corr": float(np.mean(values)) if values else 0.0,
            "max_corr": float(np.max(values)) if values else 0.0,
            "symbol_count": float(len(indices)),
        }
    return summary


def _cluster_memberships_for_symbol(
    symbol: str,
    symbol_to_clusters: Dict[str, List[str]],
    symbol_to_cluster: Dict[str, Any],
) -> List[str]:
    clusters = [
        str(cluster)
        for cluster in list(symbol_to_clusters.get(symbol, []) or [])
        if str(cluster)
    ]
    if clusters:
        return clusters
    single = symbol_to_cluster.get(symbol)
    if isinstance(single, (list, tuple, set)):
        return [str(cluster) for cluster in single if str(cluster)]
    if single:
        return [str(single)]
    return []


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
    corr_mat = estimate_correlation_matrix(returns_df, symbols, eff)
    weights = build_signed_weights_from_state(state, symbols, exclude_current_bar=True)
    notionals = build_notional_vector(state, symbols, exclude_current_bar=True)
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
            "correlation": corr_mat,
            "notionals": notionals,
        }

    z = stats.norm.ppf(eff.confidence_level)
    t = np.sqrt(_risk_horizon_bar_count(state, eff))
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
        "correlation": corr_mat,
        "notionals": notionals,
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


def _state_account_currency(state: PortfolioState) -> str:
    account = getattr(state, "account", None)
    currency = None
    if account is not None:
        currency = (
            getattr(account, "currency", None)
            or dict(getattr(account, "metadata", {}) or {}).get("currency")
            or dict(getattr(account, "metadata", {}) or {}).get("currency_code")
        )
    token = str(currency or "USD").upper().strip()
    return token or "USD"


def _market_price_for_symbol_state(
    state: PortfolioState,
    symbol: str,
    *,
    exclude_current_bar: bool = False,
) -> Optional[float]:
    market = state.markets.get(symbol)
    if market is None:
        return None
    bars = market.bars
    if exclude_current_bar and len(bars) > 1:
        bars = bars.iloc[:-1]
    close_col = "Close" if "Close" in bars.columns else "close"
    if close_col not in bars.columns or bars.empty:
        return None
    try:
        price = float(bars[close_col].iloc[-1])
    except Exception:
        return None
    return price if price > 0.0 else None


def _convert_value_to_account_currency(
    value: float,
    currency: Optional[str],
    account_currency: Optional[str],
    price_lookup,
) -> float:
    amount = float(value or 0.0)
    source = str(currency or "").upper().strip()
    target = str(account_currency or "").upper().strip()
    if amount == 0.0 or not source or not target or source == target:
        return amount
    rate = _currency_conversion_rate(source, target, price_lookup)
    if rate is None or rate <= 0.0:
        return amount
    return float(amount * rate)


def _currency_conversion_rate(
    source: str,
    target: str,
    price_lookup,
) -> Optional[float]:
    if source == target:
        return 1.0

    direct = _direct_currency_conversion_rate(source, target, price_lookup)
    if direct is not None:
        return direct

    for bridge in _FX_BRIDGE_CURRENCIES:
        if bridge in {source, target}:
            continue
        leg_one = _direct_currency_conversion_rate(source, bridge, price_lookup)
        if leg_one is None:
            continue
        leg_two = _direct_currency_conversion_rate(bridge, target, price_lookup)
        if leg_two is None:
            continue
        return float(leg_one * leg_two)

    return None


def _direct_currency_conversion_rate(
    source: str,
    target: str,
    price_lookup,
) -> Optional[float]:
    direct_symbol = f"{source}{target}"
    direct_price = price_lookup(direct_symbol)
    if direct_price is not None and direct_price > 0.0:
        return float(direct_price)

    inverse_symbol = f"{target}{source}"
    inverse_price = price_lookup(inverse_symbol)
    if inverse_price is not None and inverse_price > 0.0:
        return float(1.0 / inverse_price)

    return None
