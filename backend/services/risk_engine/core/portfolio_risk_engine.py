"""Shared portfolio risk math and data access helpers."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

from backend.services.risk_engine.limits import RiskLimits
from backend.services.risk_engine.metrics.math import compute_portfolio_var_es, estimate_margin_used
from backend.services.risk_engine.models import PortfolioState
from backend.common.logger import logger


class PortfolioRiskEngine:
    """Own portfolio math and raw market-data access for risk workflows."""

    def __init__(
        self,
        mt5_client=None,
        timeframe: str = "D1",
        start_pos: int = 0,
        end_pos: int = 500,
    ):
        self.mt5_client = mt5_client
        self.timeframe = timeframe
        self.start_pos = start_pos
        self.end_pos = end_pos

    def compute_portfolio_risk(
        self,
        positions: Dict[str, float],
        equity: float,
        limits: RiskLimits,
    ) -> Tuple[float, float, Optional[float], Optional[Dict[str, float]]]:
        """Compute portfolio VaR/ES from client-backed positions."""
        if not positions:
            return 0.0, 0.0, 0.0, {}

        symbols = list(positions.keys())
        data = self.get_data(symbols, exclude_current_bar=True)

        returns_df = self.build_returns_df(data, symbols)
        need = max(limits.vol_lookback, limits.corr_lookback)
        if returns_df.empty or returns_df.dropna().shape[0] < need:
            logger.warning(
                "PortfolioRiskEngine: insufficient returns data for VaR/ES (symbols=%s, rows=%s, need=%s)",
                symbols,
                int(returns_df.dropna().shape[0]) if not returns_df.empty else 0,
                need,
            )
            return float("inf"), float("inf"), self.estimate_margin_used(positions), None

        cov = self.estimate_covariance(returns_df, symbols, limits)
        weights = self.build_signed_weights_from_positions(positions, data, symbols)

        port_var = float(weights.T @ cov @ weights)
        port_std = float(np.sqrt(max(port_var, 0.0)))

        portfolio_value = self.portfolio_notional_value(positions, data, symbols)
        if portfolio_value <= 0 or port_std <= 0:
            logger.warning(
                "PortfolioRiskEngine: invalid portfolio inputs for VaR/ES (portfolio_value=%s, port_std=%s, symbols=%s)",
                portfolio_value,
                port_std,
                symbols,
            )
            return float("inf"), float("inf"), self.estimate_margin_used(positions), None

        z = stats.norm.ppf(limits.confidence_level)
        t = np.sqrt(limits.time_horizon_days)
        var_dollar = z * port_std * t * portfolio_value
        alpha = limits.confidence_level
        phi = stats.norm.pdf(z)
        es_dollar = (phi / (1.0 - alpha)) * port_std * t * portfolio_value
        rc_pct = self.compute_risk_contributions_pct(weights, cov, symbols)
        margin_used = self.estimate_margin_used(positions)
        return float(var_dollar), float(es_dollar), margin_used, rc_pct

    def compute_portfolio_risk_from_state(
        self,
        state: PortfolioState,
        limits: Optional[RiskLimits] = None,
    ) -> Tuple[float, float, Optional[float], Optional[Dict[str, float]]]:
        """Compute portfolio VaR/ES from canonical state."""
        var_value, es_value, rc_map, _ = compute_portfolio_var_es(state, limits=limits)
        return float(var_value), float(es_value), estimate_margin_used(state), rc_map

    def estimate_covariance(
        self,
        returns_df: pd.DataFrame,
        symbols: List[str],
        limits: RiskLimits,
    ) -> np.ndarray:
        """Estimate covariance using the current governor formula."""
        r = returns_df[symbols].dropna()
        vol = r.rolling(limits.vol_lookback).std().iloc[-1].values
        vol = np.nan_to_num(vol, nan=0.0)

        rolling_corr = r.rolling(limits.corr_lookback).corr()
        last_ts = rolling_corr.index.get_level_values(0).unique()[-1]
        corr_mat = (
            rolling_corr.loc[last_ts].reindex(index=symbols, columns=symbols).values
        )
        corr_mat = np.nan_to_num(corr_mat, nan=0.0)
        np.fill_diagonal(corr_mat, 1.0)
        corr_mat = self.apply_corr_floors(corr_mat, limits)
        return np.outer(vol, vol) * corr_mat

    def apply_corr_floors(self, corr_mat: np.ndarray, limits: RiskLimits) -> np.ndarray:
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

    def build_weights_from_positions(
        self,
        positions: Dict[str, float],
        historical_data: Dict[str, pd.DataFrame],
        symbols: List[str],
    ) -> np.ndarray:
        """Build absolute notional weights from raw positions."""
        notionals = []
        for symbol in symbols:
            notionals.append(
                abs(
                    self.symbol_notional_value(
                        symbol,
                        float(positions.get(symbol, 0.0)),
                        historical_data,
                    )
                )
            )

        total = float(np.sum(notionals))
        if total <= 0:
            return np.zeros(len(symbols), dtype=float)
        return np.array([n / total for n in notionals], dtype=float)

    def build_signed_weights_from_positions(
        self,
        positions: Dict[str, float],
        historical_data: Dict[str, pd.DataFrame],
        symbols: List[str],
    ) -> np.ndarray:
        """Build signed notional weights normalized by gross absolute notional."""
        signed_notionals = []
        gross_notionals = []
        for symbol in symbols:
            notional = self.symbol_notional_value(
                symbol,
                float(positions.get(symbol, 0.0)),
                historical_data,
            )
            signed_notionals.append(float(notional))
            gross_notionals.append(abs(float(notional)))

        total = float(np.sum(gross_notionals))
        if total <= 0:
            return np.zeros(len(symbols), dtype=float)
        return np.array([n / total for n in signed_notionals], dtype=float)

    def compute_risk_contributions_pct(
        self,
        weights: np.ndarray,
        cov: np.ndarray,
        symbols: List[str],
    ) -> Dict[str, float]:
        """Compute percentage contribution to total variance."""
        port_var = float(weights.T @ cov @ weights)
        if port_var <= 0:
            return dict.fromkeys(symbols, 0.0)

        mrc = cov @ weights
        rc = weights * mrc
        rc_pct = rc / port_var
        return {symbols[i]: float(rc_pct[i]) for i in range(len(symbols))}

    def portfolio_correlation_map(
        self,
        weights: np.ndarray,
        cov: np.ndarray,
        symbols: List[str],
    ) -> Dict[str, float]:
        """Compute symbol-to-portfolio correlation map."""
        port_var = float(weights.T @ cov @ weights)
        if port_var <= 0:
            return dict.fromkeys(symbols, 0.0)

        port_std = float(np.sqrt(port_var))
        cov_w = cov @ weights
        corr_map: Dict[str, float] = {}
        for i, symbol in enumerate(symbols):
            sym_var = float(cov[i, i])
            if sym_var <= 0:
                corr_map[symbol] = 0.0
            else:
                corr_map[symbol] = float(cov_w[i] / (np.sqrt(sym_var) * port_std))
        return corr_map

    def estimate_margin_used(self, positions: Dict[str, float]) -> Optional[float]:
        """Estimate current margin usage for raw positions."""
        if not positions:
            return 0.0
        if self.mt5_client is None or not hasattr(self.mt5_client, "get_margin_required"):
            return None

        total = 0.0
        for sym, lots in positions.items():
            if lots == 0:
                continue
            margin_required = self.mt5_client.get_margin_required(sym, lots)
            if margin_required is None:
                return None
            total += abs(float(margin_required))
        return float(total)

    def get_data(
        self,
        symbols: List[str],
        exclude_current_bar: bool = True,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch historical bars for the supplied symbols."""
        all_data: Dict[str, pd.DataFrame] = {}
        if self.mt5_client is None:
            return all_data
        for symbol in symbols:
            df = self.mt5_client.get_bars(
                symbol=symbol,
                timeframe=self.timeframe,
                count=self.end_pos - self.start_pos,
                start_pos=self.start_pos,
            )
            if df is None or df.empty or "close" not in df.columns:
                continue

            if "close" in df.columns and "Close" not in df.columns:
                df = df.rename(columns={"close": "Close"})

            if exclude_current_bar and len(df) > 1:
                df = df.iloc[:-1]
            all_data[symbol] = df
        return all_data

    def build_returns_df(
        self,
        data: Dict[str, pd.DataFrame],
        symbols: List[str],
    ) -> pd.DataFrame:
        """Build log returns from raw bar frames."""
        cols = {}
        for symbol in symbols:
            df = data.get(symbol)
            if df is None or df.empty:
                continue
            px = df["Close"].astype(float)
            cols[symbol] = np.log(px / px.shift(1))
        if not cols:
            return pd.DataFrame()
        return pd.DataFrame(cols).dropna(how="all")

    def portfolio_notional_value(
        self,
        positions: Dict[str, float],
        historical_data: Dict[str, pd.DataFrame],
        symbols: List[str],
    ) -> float:
        """Compute total absolute notional exposure."""
        total = 0.0
        for symbol in symbols:
            total += abs(
                self.symbol_notional_value(
                    symbol,
                    float(positions.get(symbol, 0.0)),
                    historical_data,
                )
            )
        return float(total)

    def symbol_notional_value(
        self,
        symbol: str,
        lots: float,
        historical_data: Dict[str, pd.DataFrame],
    ) -> float:
        """Compute symbol notional normalized to account currency."""
        df = historical_data.get(symbol)
        if df is None or df.empty:
            logger.warning("PortfolioRiskEngine: missing historical data for %s", symbol)
            return 0.0
        price = float(df["Close"].iloc[-1])

        if self.mt5_client is None:
            return 0.0
        info = self.mt5_client.get_symbol_info(symbol)
        if info is None:
            logger.warning("PortfolioRiskEngine: missing symbol_info for %s", symbol)
            return 0.0

        contract_size = (
            float(info.get("trade_contract_size", 0.0))
            if isinstance(info, dict)
            else float(getattr(info, "trade_contract_size", 0.0))
        )
        profit_currency = (
            str(info.get("currency_profit", "") or info.get("profit_currency", "") or "")
            if isinstance(info, dict)
            else str(
                getattr(info, "currency_profit", getattr(info, "profit_currency", "")) or ""
            )
        ).upper().strip() or self._symbol_quote_currency(symbol)
        account_currency = self._account_currency()
        if contract_size > 0:
            raw_notional = float(lots * contract_size * price)
            return self._convert_value_to_account_currency(
                raw_notional,
                profit_currency,
                account_currency,
                historical_data,
            )

        tick_value = (
            float(info.get("trade_tick_value", 0.0))
            if isinstance(info, dict)
            else float(getattr(info, "trade_tick_value", 0.0))
        )
        tick_size = (
            float(info.get("trade_tick_size", 0.0))
            if isinstance(info, dict)
            else float(getattr(info, "trade_tick_size", 0.0))
        )
        if tick_value > 0 and tick_size > 0:
            value_per_price_unit = tick_value / tick_size
            raw_notional = float(lots * value_per_price_unit * price)
            return self._convert_value_to_account_currency(
                raw_notional,
                profit_currency,
                account_currency,
                historical_data,
            )

        logger.warning(
            "PortfolioRiskEngine: no valid contract/tick values for %s (contract_size=%s, tick_value=%s, tick_size=%s)",
            symbol,
            contract_size,
            tick_value,
            tick_size,
        )
        return 0.0

    def _account_currency(self) -> str:
        if self.mt5_client is not None:
            if hasattr(self.mt5_client, "get_account_currency"):
                try:
                    currency = self.mt5_client.get_account_currency()
                    if currency:
                        token = str(currency).upper().strip()
                        if token:
                            return token
                except Exception:
                    pass
            if hasattr(self.mt5_client, "account_info"):
                try:
                    raw_account = self.mt5_client.account_info()
                    if raw_account is not None:
                        if hasattr(raw_account, "_asdict"):
                            raw_account = raw_account._asdict()
                        if isinstance(raw_account, dict):
                            currency = raw_account.get("currency") or raw_account.get("currency_code")
                        else:
                            currency = getattr(raw_account, "currency", getattr(raw_account, "currency_code", None))
                        if currency:
                            token = str(currency).upper().strip()
                            if token:
                                return token
                except Exception:
                    pass
        return "USD"

    def _convert_value_to_account_currency(
        self,
        value: float,
        source_currency: Optional[str],
        target_currency: Optional[str],
        historical_data: Dict[str, pd.DataFrame],
    ) -> float:
        amount = float(value or 0.0)
        source = str(source_currency or "").upper().strip()
        target = str(target_currency or "").upper().strip()
        if amount == 0.0 or not source or not target or source == target:
            return amount
        rate = self._currency_conversion_rate(source, target, historical_data)
        if rate is None or rate <= 0.0:
            return amount
        return float(amount * rate)

    def _currency_conversion_rate(
        self,
        source: str,
        target: str,
        historical_data: Dict[str, pd.DataFrame],
    ) -> Optional[float]:
        if source == target:
            return 1.0
        direct = self._direct_currency_conversion_rate(source, target, historical_data)
        if direct is not None:
            return direct
        for bridge in ("USD", "EUR", "JPY", "GBP", "CHF", "CAD", "AUD", "NZD"):
            if bridge in {source, target}:
                continue
            leg_one = self._direct_currency_conversion_rate(source, bridge, historical_data)
            if leg_one is None:
                continue
            leg_two = self._direct_currency_conversion_rate(bridge, target, historical_data)
            if leg_two is None:
                continue
            return float(leg_one * leg_two)
        return None

    def _direct_currency_conversion_rate(
        self,
        source: str,
        target: str,
        historical_data: Dict[str, pd.DataFrame],
    ) -> Optional[float]:
        direct_symbol = f"{source}{target}"
        direct_price = self._price_for_symbol(direct_symbol, historical_data)
        if direct_price is not None and direct_price > 0.0:
            return float(direct_price)
        inverse_symbol = f"{target}{source}"
        inverse_price = self._price_for_symbol(inverse_symbol, historical_data)
        if inverse_price is not None and inverse_price > 0.0:
            return float(1.0 / inverse_price)
        return None

    def _price_for_symbol(
        self,
        symbol: str,
        historical_data: Dict[str, pd.DataFrame],
    ) -> Optional[float]:
        df = historical_data.get(symbol)
        if df is not None and not df.empty and "Close" in df.columns:
            try:
                price = float(df["Close"].iloc[-1])
                if price > 0.0:
                    return price
            except Exception:
                return None
        return None

    def _symbol_quote_currency(self, symbol: str) -> Optional[str]:
        token = str(symbol).upper()
        if len(token) >= 6 and token[:6].isalpha():
            return token[3:6]
        return None

    def compute_cluster_metrics(
        self,
        positions: Dict[str, float],
        equity: float,
        symbol_to_cluster: Optional[Dict[str, Any]],
        limits: RiskLimits,
    ) -> Dict[str, Dict[str, float]]:
        """Compute per-cluster VaR/ES metrics."""
        if not positions or not symbol_to_cluster:
            return {}
        clusters = self.group_positions_by_cluster(positions, symbol_to_cluster)
        out: Dict[str, Dict[str, float]] = {}
        for cluster_key, cluster_positions in clusters.items():
            cluster_var, cluster_es, _, _ = self.compute_portfolio_risk(
                cluster_positions,
                equity,
                limits,
            )
            out[cluster_key] = {"var": cluster_var, "es": cluster_es}
        return out

    def compute_cluster_metrics_from_state(
        self,
        state: PortfolioState,
        limits: Optional[RiskLimits] = None,
    ) -> Dict[str, Dict[str, float]]:
        """Compute per-cluster VaR/ES metrics from canonical state."""
        effective = limits or state.limits or RiskLimits()
        out: Dict[str, Dict[str, float]] = {}
        for cluster_key, cluster_positions in self.group_positions_by_cluster(
            state.position_map,
            state.symbol_to_clusters or state.symbol_to_cluster,
        ).items():
            subset_state = PortfolioState(
                account=state.account,
                positions=[pos for pos in state.positions if pos.symbol in cluster_positions],
                symbols={key: value for key, value in state.symbols.items() if key in cluster_positions},
                markets={key: value for key, value in state.markets.items() if key in cluster_positions},
                limits=effective,
                symbol_to_cluster={key: value for key, value in state.symbol_to_cluster.items() if key in cluster_positions},
                symbol_to_clusters={
                    key: value
                    for key, value in getattr(state, "symbol_to_clusters", {}).items()
                    if key in cluster_positions
                },
                validation_summary=state.validation_summary,
                exposures={key: value for key, value in state.exposures.items() if key in cluster_positions},
                as_of=state.as_of,
                metadata=state.metadata,
            )
            cluster_var, cluster_es, _, _ = self.compute_portfolio_risk_from_state(
                subset_state,
                limits=effective,
            )
            out[cluster_key] = {"var": cluster_var, "es": cluster_es}
        return out

    def group_positions_by_cluster(
        self,
        positions: Dict[str, float],
        symbol_to_cluster: Dict[str, Any],
    ) -> Dict[str, Dict[str, float]]:
        """Group positions by cluster key."""
        clusters: Dict[str, Dict[str, float]] = {}
        for sym, lots in positions.items():
            cluster_keys = self._iter_cluster_keys(symbol_to_cluster.get(sym))
            if not cluster_keys:
                continue
            for cluster_key in cluster_keys:
                clusters.setdefault(cluster_key, {})[sym] = lots
        return clusters

    @staticmethod
    def _iter_cluster_keys(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if str(item)]
        token = str(value)
        return [token] if token else []

    def propose_rc_rebalance(
        self,
        positions: Dict[str, float],
        target_rc_budget: Dict[str, float],
        limits: RiskLimits,
        max_iters: int = 10,
        step_frac: float = 0.10,
    ) -> Dict[str, float]:
        """Propose position adjustments to align with risk contribution budget."""
        if not positions or len(positions) < 2:
            return {}

        symbols = list(positions.keys())
        data = self.get_data(symbols, exclude_current_bar=True)
        returns_df = self.build_returns_df(data, symbols)
        need = max(limits.vol_lookback, limits.corr_lookback)
        if returns_df.empty or returns_df.dropna().shape[0] < need:
            return {}

        cov = self.estimate_covariance(returns_df, symbols, limits)
        target = {s: float(target_rc_budget.get(s, 0.0)) for s in symbols}
        total = sum(target.values())
        if total <= 0:
            target = {s: 1.0 / len(symbols) for s in symbols}
        else:
            target = {s: v / total for s, v in target.items()}

        pos_work = dict(positions)
        proposed = dict.fromkeys(symbols, 0.0)

        for _ in range(max_iters):
            weights = self.build_weights_from_positions(pos_work, data, symbols)
            rc = self.compute_risk_contributions_pct(weights, cov, symbols)
            deviation = {s: rc.get(s, 0.0) - target.get(s, 0.0) for s in symbols}
            over_sym, over_amt = max(deviation.items(), key=lambda x: x[1])
            under_sym, under_amt = min(deviation.items(), key=lambda x: x[1])

            if (
                over_amt <= limits.rc_rebalance_tolerance
                and abs(under_amt) <= limits.rc_rebalance_tolerance
            ):
                break

            if over_amt > limits.rc_rebalance_tolerance:
                delta = -step_frac * pos_work[over_sym]
                pos_work[over_sym] += delta
                proposed[over_sym] += delta

            if under_amt < -limits.rc_rebalance_tolerance:
                base = pos_work.get(under_sym, 0.0)
                bump = step_frac * (abs(base) if abs(base) > 1e-6 else 0.1)
                pos_work[under_sym] += bump
                proposed[under_sym] += bump

        return {s: d for s, d in proposed.items() if abs(d) > 1e-8}
