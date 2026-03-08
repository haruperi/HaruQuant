"""
Strategy Scorecard Module.

Computes the FINAL_SCORE (0-100) for SQX strategies based on:
- Hard filter rejection
- Normalized pillar scores (EDGE/ROBUST/STABILITY/RISK/SIMPLE)
- Soft fragility penalty
- Per-symbol ranking
"""

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


# =============================
# Normalization helpers
# =============================
def clamp(x: float, lo: float, hi: float) -> float:
    """Clamp a value between a minimum and maximum."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return float("nan")
    return min(max(x, lo), hi)


def norm_up(x: float, lo: float, hi: float) -> float:
    """Normalize a value (higher is better) to 0-1 range."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return float("nan")
    if hi == lo:
        return 0.0
    return clamp((x - lo) / (hi - lo), 0.0, 1.0)


def norm_down(x: float, lo: float, hi: float) -> float:
    """Normalize a value (lower is better) to 0-1 range."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return float("nan")
    if hi == lo:
        return 0.0
    return clamp((hi - x) / (hi - lo), 0.0, 1.0)


def logistic(x: float, mid: float, steep: float) -> float:
    """Apply logistic function normalization."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return float("nan")
    z = -steep * (x - mid)
    z = clamp(z, -60.0, 60.0)
    return 1.0 / (1.0 + math.exp(z))


def ratio_score(r: float, lo: float = 0.50, hi: float = 1.10) -> float:
    """Score a ratio value using norm_up."""
    if r is None or (isinstance(r, float) and math.isnan(r)):
        return float("nan")
    return norm_up(r, lo, hi)


def _nan_to_default_series(s: pd.Series, default: float) -> pd.Series:
    return s.fillna(default)


def safe_div(a: float, b: float, default: float = np.nan) -> float:
    """Safely divide two numbers, returning default on zero division or error."""
    try:
        if b == 0 or (isinstance(b, float) and math.isnan(b)):
            return default
        return a / b
    except Exception:
        return default


def _mean_score(scores: Dict[str, pd.Series], default: float = 0.0) -> pd.Series:
    if not scores:
        return pd.Series([default] * 0)
    df = pd.DataFrame(scores)
    df = df.astype(float)
    mean = df.mean(axis=1, skipna=True)
    mean = mean.fillna(default)
    return mean


def _weighted_sum(
    scores: Dict[str, pd.Series], weights: Dict[str, float], default: float = 0.0
) -> pd.Series:
    if not scores:
        return pd.Series([default] * 0)
    df = pd.DataFrame(scores)
    df = df.astype(float).fillna(default)
    weight_vec = np.array([weights[k] for k in df.columns])
    weighted = df.values * weight_vec
    return pd.Series(weighted.sum(axis=1), index=df.index)


@dataclass
class ScoreConfig:
    """Configuration for the scorecard."""

    thresholds: Dict[str, Any] = field(
        default_factory=lambda: {
            "min_trades": 300,
            "min_pf_final": 1.00,
            "min_net_profit": 0.0,
            "max_dd_pct": 40.0,
            "min_ret_dd": 0.30,
        }
    )
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "EDGE": 0.30,
            "ROBUST": 0.30,
            "STABILITY": 0.20,
            "RISK": 0.15,
            "SIMPLE": 0.05,
        }
    )
    symbol_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)


class StrategyScorecard:
    """Computes scores for strategy DataFrames."""

    def __init__(self, config: Optional[ScoreConfig] = None):
        """Initialize the StrategyScorecard with an optional configuration."""
        self.config = config or ScoreConfig()

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Run the full scoring pipeline on the dataframe."""
        if df.empty:
            return df

        df = self._ensure_numeric(df)
        df = self._compute_derived(df)
        df = self._score_pillars(df)
        df = self._apply_hard_filters(df)
        df = self._apply_soft_penalties(df)
        df = self._compute_final_score(df)
        df = self._rank_within_symbol(df)
        return df

    def _ensure_numeric(self, df: pd.DataFrame) -> pd.DataFrame:
        # Columns that should be numeric
        # We assume the DF comes from DB or CSV with mostly correct types,
        # but let's enforce core metrics
        cols = [
            "trades",
            "profit_factor",
            "net_profit",
            "max_drawdown_pct",
            "return_pct",
            "annual_return_pct",
            "ret_dd",
            "oos_profit_factor",
            "oos_ret_dd",
            "oos_annual_return_pct",
            "oos_profitable_windows_ratio",
            "spread_p99_retdd_ratio",
            "spread_max_retdd_ratio",
            "slip_retdd_ratio",
            "delay_pf_ratio",
            "mc_survival_rate",
            "mc_retdd_p95_ratio",
            "mc_dd_inflation",
            "mc_overall_survival_rate",
            "mc_overall_retdd_ratio",
            "stagnation_days",
            "max_consecutive_losses",
            "pf_degradation_ratio",
            "time_in_market_pct",
            "parameter_count",
            "indicator_count",
            "mtf_count",
            "param_perturb_profitable_rate",
            "history_perturb_pf_ratio",
            "ret_dd_ratio",
            "win_percent",
            "stagnation",
            "a1_profit_factor",
            "a1_ret_dd_ratio",
            "a1_annual_return_pct",
            "a1_trades",
            "a1_net_profit",
            "a1_max_drawdown_pct",
            "a1_edge_score",
            "a2_profit_factor",
            "a2_ret_dd_ratio",
            "a2_annual_return_pct",
            "a2_trades",
            "a2_net_profit",
            "a2_max_drawdown_pct",
            "a2_edge_score",
            "e1_profit_factor",
            "e1_ret_dd_ratio",
            "e1_annual_return_pct",
            "e1_trades",
            "e1_net_profit",
            "e1_max_drawdown_pct",
            "e1_edge_score",
        ]
        for c in cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    def _compute_derived(self, df: pd.DataFrame) -> pd.DataFrame:
        if "win_rate" in df.columns:
            wr = df["win_rate"].copy()
            # If win_rate > 1 (e.g. 55.5), convert to 0.555. 0-1 scale needed.
            if np.nanmedian(wr.values) > 1.0:
                df["win_rate"] = wr / 100.0

        if "gross_loss" in df.columns:
            df["gross_loss"] = df["gross_loss"].abs()

        if "win_percent" in df.columns:
            wp = df["win_percent"].copy()
            if np.nanmedian(wp.values) > 1.0:
                df["win_percent"] = wp / 100.0

        if "ret_dd" not in df.columns and {"return_pct", "max_drawdown_pct"}.issubset(
            df.columns
        ):
            df["ret_dd"] = df.apply(
                lambda r: safe_div(r["return_pct"], r["max_drawdown_pct"]), axis=1
            )

        if "ret_dd" not in df.columns and "ret_dd_ratio" in df.columns:
            df["ret_dd"] = df["ret_dd_ratio"]

        if "stagnation_days" not in df.columns and "stagnation" in df.columns:
            df["stagnation_days"] = df["stagnation"]

        # Basic degradations if OOS columns exist
        if "pf_degradation_ratio" not in df.columns and {
            "oos_profit_factor",
            "is_profit_factor",
        }.issubset(df.columns):
            df["pf_degradation_ratio"] = df.apply(
                lambda r: safe_div(r["oos_profit_factor"], r["is_profit_factor"]),
                axis=1,
            )

        return df

    def _apply_hard_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        thr = self.config.thresholds
        defaults = {
            "min_trades": float(thr.get("min_trades", 300)),
            "min_pf_final": float(thr.get("min_pf_final", 1.00)),
            "min_net_profit": float(thr.get("min_net_profit", 0.0)),
            "max_dd_pct": float(thr.get("max_dd_pct", 40.0)),
            "min_ret_dd": float(thr.get("min_ret_dd", 0.30)),
        }

        # We'll stick "rejected" (lowercase to match DB schema)
        df["rejected"] = 0

        for idx, row in df.iterrows():
            if "stage" in df.columns:
                stage = str(row.get("stage", ""))
                if stage and stage != "F1_FINAL":
                    continue

            if self._is_hard_fail(row, defaults):
                df.at[idx, "rejected"] = 1

        return df

    def _is_hard_fail(self, row: pd.Series, defaults: Dict[str, float]) -> bool:
        """Check if a single row fails hard filters."""
        sym = str(row.get("symbol", ""))
        ovr = self.config.symbol_overrides.get(sym, {})

        min_trades = float(ovr.get("min_trades", defaults["min_trades"]))
        min_pf = float(ovr.get("min_pf_final", defaults["min_pf_final"]))
        min_net_profit = float(ovr.get("min_net_profit", defaults["min_net_profit"]))
        max_dd = float(ovr.get("max_dd_pct", defaults["max_dd_pct"]))
        min_ret_dd = float(ovr.get("min_ret_dd", defaults["min_ret_dd"]))

        trades = row.get("trades", np.nan)
        # Use oos_profit_factor if available as primary, else profit_factor
        pf = (
            row.get("oos_profit_factor")
            if pd.notna(row.get("oos_profit_factor"))
            else row.get("profit_factor", np.nan)
        )
        netp = row.get("net_profit", np.nan)
        dd = (
            row.get("max_drawdown_pct")
            if pd.notna(row.get("max_drawdown_pct"))
            else row.get("drawdown_pct", np.nan)
        )
        retdd = row.get("ret_dd", row.get("ret_dd_ratio", np.nan))

        # Trade count
        if not (
            isinstance(trades, (int, float))
            and not math.isnan(float(trades))
            and float(trades) >= min_trades
        ):
            return True

        # Profit Factor
        if isinstance(pf, (int, float)) and not math.isnan(float(pf)):
            if float(pf) < min_pf:
                return True
        else:
            return True  # Missing PF is fail

        # Net Profit
        if isinstance(netp, (int, float)) and not math.isnan(float(netp)):
            if float(netp) <= min_net_profit:
                return True
        else:
            return True  # Missing NP is fail

        # Drawdown
        if isinstance(dd, (int, float)) and not math.isnan(float(dd)):
            if float(dd) > max_dd:
                return True
        else:
            # Fallback: Ret/DD check if DD% missing
            if not (
                isinstance(retdd, (int, float))
                and not math.isnan(float(retdd))
                and float(retdd) >= min_ret_dd
            ):
                return True

        return False

    def _score_pillars(self, df: pd.DataFrame) -> pd.DataFrame:
        # EDGE
        def edge_from_prefix(prefix: str) -> pd.Series:
            pf_col = f"{prefix}_profit_factor"
            retdd_col = f"{prefix}_ret_dd_ratio"
            ann_col = f"{prefix}_annual_return_pct"
            if not ({pf_col, retdd_col, ann_col}.intersection(df.columns)):
                return pd.Series([np.nan] * len(df), index=df.index)
            pf = (
                df[pf_col]
                if pf_col in df.columns
                else pd.Series([np.nan] * len(df), index=df.index)
            )
            retdd = (
                df[retdd_col]
                if retdd_col in df.columns
                else pd.Series([np.nan] * len(df), index=df.index)
            )
            ann = (
                df[ann_col]
                if ann_col in df.columns
                else pd.Series([np.nan] * len(df), index=df.index)
            )
            pf_s = pf.apply(lambda x: logistic(x, mid=1.20, steep=4.0))
            retdd_s = retdd.apply(lambda x: logistic(x, mid=0.80, steep=3.0))
            ann_s = ann.apply(lambda x: norm_up(x, lo=0.0, hi=40.0))
            winwin_s = pd.Series([0.5] * len(df), index=df.index)
            return 0.40 * pf_s + 0.35 * retdd_s + 0.15 * ann_s + 0.10 * winwin_s

        edge_a1 = edge_from_prefix("a1")
        edge_a2 = edge_from_prefix("a2")
        edge_e1 = edge_from_prefix("e1")

        df["a1_edge_score"] = edge_a1
        df["a2_edge_score"] = edge_a2
        df["e1_edge_score"] = edge_e1

        edge_weights = {"a1": 10.0, "a2": 8.0, "e1": 12.0}
        df["edge_score"] = _weighted_sum(
            {"a1": edge_a1, "a2": edge_a2, "e1": edge_e1},
            edge_weights,
            default=0.0,
        )

        # ROBUST
        def rs(col: str, default: float = 0.5) -> pd.Series:
            return (
                df[col].apply(lambda x: ratio_score(x))
                if col in df.columns
                else pd.Series([default] * len(df), index=df.index)
            )

        spread_s = rs("spread_p99_retdd_ratio", np.nan)
        slip_s = rs("slip_retdd_ratio", np.nan)
        delay_s = rs("delay_pf_ratio", np.nan)

        mc_surv_s = (
            df["mc_survival_rate"].apply(lambda x: clamp(x, 0.0, 1.0))
            if "mc_survival_rate" in df.columns
            else pd.Series([np.nan] * len(df), index=df.index)
        )
        mc_retdd_s = rs("mc_retdd_p95_ratio", np.nan)
        dd_infl_s = (
            df["mc_dd_inflation"].apply(lambda x: norm_down(x, lo=1.0, hi=1.5))
            if "mc_dd_inflation" in df.columns
            else pd.Series([np.nan] * len(df), index=df.index)
        )
        mc_all_surv_s = (
            df["mc_overall_survival_rate"].apply(lambda x: clamp(x, 0.0, 1.0))
            if "mc_overall_survival_rate" in df.columns
            else pd.Series([np.nan] * len(df), index=df.index)
        )
        mc_all_retdd_s = rs("mc_overall_retdd_ratio", np.nan)

        c1_score = _mean_score(
            {"survival": mc_surv_s, "retdd": mc_retdd_s},
            default=0.0,
        )
        c2_score = dd_infl_s
        c3_score = pd.Series([np.nan] * len(df), index=df.index)
        c4_score = (
            df["param_perturb_profitable_rate"].apply(
                lambda x: norm_up(x, lo=0.70, hi=0.95)
            )
            if "param_perturb_profitable_rate" in df.columns
            else pd.Series([np.nan] * len(df), index=df.index)
        )
        c5_score = rs("history_perturb_pf_ratio", np.nan)
        c6_score = _mean_score(
            {"survival": mc_all_surv_s, "retdd": mc_all_retdd_s},
            default=0.0,
        )

        robust_weights = {
            "b1": 5.0,
            "b3": 5.0,
            "b4": 5.0,
            "c1": 5.0,
            "c2": 3.0,
            "c3": 2.0,
            "c4": 2.0,
            "c5": 1.0,
            "c6": 2.0,
        }
        df["robust_score"] = _weighted_sum(
            {
                "b1": spread_s,
                "b3": slip_s,
                "b4": delay_s,
                "c1": c1_score,
                "c2": c2_score,
                "c3": c3_score,
                "c4": c4_score,
                "c5": c5_score,
                "c6": c6_score,
            },
            robust_weights,
            default=0.0,
        )

        # STABILITY
        stagn_s = (
            df["stagnation_days"].apply(lambda x: norm_down(x, lo=0.0, hi=30.0))
            if "stagnation_days" in df.columns
            else pd.Series([0.5] * len(df), index=df.index)
        )
        consec_s = (
            df["max_consecutive_losses"].apply(lambda x: norm_down(x, lo=4.0, hi=12.0))
            if "max_consecutive_losses" in df.columns
            else pd.Series([0.5] * len(df), index=df.index)
        )
        deg_pf_s = (
            df["pf_degradation_ratio"].apply(lambda x: ratio_score(x))
            if "pf_degradation_ratio" in df.columns
            else pd.Series([0.5] * len(df), index=df.index)
        )

        a2_stability = _mean_score(
            {"deg": deg_pf_s, "stagn": stagn_s, "consec": consec_s},
            default=0.0,
        )
        if "a2_profit_factor" in df.columns:
            a2_available = df["a2_profit_factor"].notna()
        elif "a2_ret_dd_ratio" in df.columns:
            a2_available = df["a2_ret_dd_ratio"].notna()
        elif "a2_trades" in df.columns:
            a2_available = df["a2_trades"].notna()
        else:
            a2_available = pd.Series([False] * len(df), index=df.index)
        a2_stability = a2_stability.where(a2_available, np.nan)
        stability_weights = {"a2": 10.0, "c2": 5.0, "c3": 5.0}
        df["stability_score"] = _weighted_sum(
            {"a2": a2_stability, "c2": c2_score, "c3": c3_score},
            stability_weights,
            default=0.0,
        )

        # RISK
        retdd_base_s = (
            df["ret_dd"].apply(lambda x: logistic(x, mid=0.80, steep=3.0))
            if "ret_dd" in df.columns
            else pd.Series([0.5] * len(df), index=df.index)
        )
        dd_s = (
            df["max_drawdown_pct"].apply(lambda x: norm_down(x, lo=10.0, hi=40.0))
            if ("max_drawdown_pct" in df.columns)
            else pd.Series([0.5] * len(df), index=df.index)
        )
        # fallback for DD if not found? max_drawdown_pct is standard in many exports

        tim_s = (
            df["time_in_market_pct"].apply(lambda x: norm_down(x, lo=20.0, hi=80.0))
            if "time_in_market_pct" in df.columns
            else pd.Series([0.5] * len(df), index=df.index)
        )

        risk_weights = {"retdd": 7.0, "dd": 5.0, "tim": 3.0}
        df["risk_score"] = _weighted_sum(
            {"retdd": retdd_base_s, "dd": dd_s, "tim": tim_s},
            risk_weights,
            default=0.0,
        )

        # SIMPLE
        if {"parameter_count", "indicator_count"}.issubset(df.columns):
            par_s = df["parameter_count"].apply(lambda x: norm_down(x, lo=5.0, hi=25.0))
            ind_s = df["indicator_count"].apply(lambda x: norm_down(x, lo=2.0, hi=12.0))
            simple_weights = {"par": 3.0, "ind": 2.0}
            df["simple_score"] = _weighted_sum(
                {"par": par_s, "ind": ind_s},
                simple_weights,
                default=0.0,
            )
        else:
            df["simple_score"] = 0.0

        return df

    def _apply_soft_penalties(self, df: pd.DataFrame) -> pd.DataFrame:
        if "param_perturb_profitable_rate" in df.columns:
            pp_s = df["param_perturb_profitable_rate"].apply(
                lambda x: norm_up(x, lo=0.70, hi=0.95)
            )
        else:
            pp_s = pd.Series([np.nan] * len(df), index=df.index)

        if "history_perturb_pf_ratio" in df.columns:
            hist_s = df["history_perturb_pf_ratio"].apply(lambda x: ratio_score(x))
        else:
            hist_s = pd.Series([np.nan] * len(df), index=df.index)

        weight_sum = (pp_s.notna().astype(float) * 0.60) + (
            hist_s.notna().astype(float) * 0.40
        )
        weighted = (pp_s.fillna(0.0) * 0.60) + (hist_s.fillna(0.0) * 0.40)
        score = weighted.div(weight_sum.where(weight_sum > 0), fill_value=1.0)
        df["fragility_penalty"] = (10.0 * (1 - score)).clip(0.0, 10.0)
        df.loc[weight_sum == 0, "fragility_penalty"] = 0.0

        if "spread_max_retdd_ratio" in df.columns:
            ratio = df["spread_max_retdd_ratio"]
            penalty = ratio.apply(
                lambda x: (
                    3.0 * (0.70 - x) / 0.70
                    if isinstance(x, (int, float))
                    and not math.isnan(float(x))
                    and x < 0.70
                    else 0.0
                )
            )
            df["fragility_penalty"] = (df["fragility_penalty"] + penalty).clip(
                0.0, 15.0
            )

        return df

    def _compute_final_score(self, df: pd.DataFrame) -> pd.DataFrame:
        base_points = (
            df["edge_score"]
            + df["robust_score"]
            + df["stability_score"]
            + df["risk_score"]
            + df["simple_score"]
        ).clip(0.0, 100.0)

        df["base_score_0_1"] = (base_points / 100.0).round(4)
        df["final_score"] = (
            (base_points - df["fragility_penalty"]).clip(0.0, 100.0).round(3)
        )

        # Zero out rejected strategies
        df.loc[df["rejected"] == 1, "final_score"] = 0.0
        return df

    def _rank_within_symbol(self, df: pd.DataFrame) -> pd.DataFrame:
        def col_or_default(c: str, default: float) -> pd.Series:
            return (
                df[c]
                if c in df.columns
                else pd.Series([default] * len(df), index=df.index)
            )

        df["_tb1"] = col_or_default("mc_overall_survival_rate", 0.5)
        df["_tb2"] = col_or_default("mc_overall_retdd_ratio", 0.9)
        df["_tb3"] = col_or_default("parameter_count", 999.0)  # lower better
        df["_tb4"] = col_or_default("max_drawdown_pct", 999.0)  # lower better

        df = df.sort_values(
            by=["symbol", "final_score", "_tb1", "_tb2", "_tb3", "_tb4"],
            ascending=[True, False, False, False, True, True],
            kind="mergesort",
        ).copy()

        df["rank_in_symbol"] = df.groupby("symbol").cumcount() + 1
        return df.drop(columns=["_tb1", "_tb2", "_tb3", "_tb4"], errors="ignore")
