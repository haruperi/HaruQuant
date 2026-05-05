"""Deterministic scenario evaluation on top of canonical portfolio state."""

from __future__ import annotations

from typing import List

import numpy as np

from services.risk.models import PortfolioState

from ..metrics.math import (
    build_notional_vector,
    build_weights_from_state,
    compute_portfolio_var_es,
    state_symbol_list,
)
from .models import ScenarioResult, StressScenario
from .registry import ScenarioRegistry, build_default_scenario_registry


def evaluate_scenarios(
    state: PortfolioState,
    registry: ScenarioRegistry | None = None,
) -> List[ScenarioResult]:
    """Evaluate the registered deterministic stress scenarios."""
    active_registry = registry or build_default_scenario_registry()
    _, _, _, artifacts = compute_portfolio_var_es(state)
    symbols = list(artifacts.get("symbols", []))
    if not symbols:
        return []

    portfolio_notional = float(artifacts.get("portfolio_notional", 0.0) or 0.0)
    portfolio_std = float(artifacts.get("portfolio_std", 0.0) or 0.0)
    base_var = float("inf")
    base_es = float("inf")
    try:
        base_var, base_es, _, _ = compute_portfolio_var_es(state)
    except Exception:
        pass

    results: List[ScenarioResult] = []
    for scenario in active_registry.scenarios:
        results.append(
            _evaluate_one(
                state=state,
                scenario=scenario,
                symbols=symbols,
                portfolio_notional=portfolio_notional,
                portfolio_std=portfolio_std,
                base_var=base_var,
                base_es=base_es,
            )
        )
    return results


def _evaluate_one(
    state: PortfolioState,
    scenario: StressScenario,
    symbols: list[str],
    portfolio_notional: float,
    portfolio_std: float,
    base_var: float,
    base_es: float,
) -> ScenarioResult:
    notionals = build_notional_vector(state, symbols, exclude_current_bar=True)
    gross_exposure = float(np.sum(notionals))
    largest_single = float(np.max(notionals)) if notionals.size else 0.0

    if scenario.name == "volatility_shock":
        sigma = float(scenario.parameters.get("shock_sigma", 2.5))
        loss = portfolio_notional * portfolio_std * sigma
        return ScenarioResult(
            name=scenario.name,
            loss=float(loss),
            stressed_var=float(base_var * sigma / 1.645) if np.isfinite(base_var) else None,
            stressed_es=float(base_es * sigma / 2.0627128075074257) if np.isfinite(base_es) else None,
            context={"description": scenario.description, **scenario.parameters},
        )

    if scenario.name == "spread_blowout":
        spread_bps = float(scenario.parameters.get("spread_bps", 20.0))
        loss = gross_exposure * (spread_bps / 10000.0)
        return ScenarioResult(
            name=scenario.name,
            loss=float(loss),
            context={"description": scenario.description, **scenario.parameters},
        )

    if scenario.name == "gap_risk":
        gap_frac = float(scenario.parameters.get("gap_frac", 0.015))
        loss = largest_single * gap_frac
        return ScenarioResult(
            name=scenario.name,
            loss=float(loss),
            context={"description": scenario.description, **scenario.parameters},
        )

    if scenario.name == "correlation_spike":
        corr_floor = float(scenario.parameters.get("corr_floor", 0.85))
        artifacts = _stressed_correlation_tail(state, corr_floor=corr_floor)
        return ScenarioResult(
            name=scenario.name,
            loss=float(max((artifacts["stressed_var"] or 0.0) - (base_var if np.isfinite(base_var) else 0.0), 0.0)),
            stressed_var=artifacts["stressed_var"],
            stressed_es=artifacts["stressed_es"],
            context={"description": scenario.description, **scenario.parameters},
        )

    if scenario.name == "liquidity_crunch":
        liquidity_cost_frac = float(scenario.parameters.get("liquidity_cost_frac", 0.0075))
        loss = gross_exposure * liquidity_cost_frac
        return ScenarioResult(
            name=scenario.name,
            loss=float(loss),
            context={"description": scenario.description, **scenario.parameters},
        )

    return ScenarioResult(
        name=scenario.name,
        loss=0.0,
        context={"description": scenario.description, **scenario.parameters},
    )


def _stressed_correlation_tail(
    state: PortfolioState,
    corr_floor: float,
) -> dict[str, float | None]:
    _, _, _, artifacts = compute_portfolio_var_es(state)
    symbols = state_symbol_list(state)
    weights = artifacts.get("weights")
    cov = artifacts.get("covariance")
    portfolio_notional = float(artifacts.get("portfolio_notional", 0.0) or 0.0)
    if weights is None or cov is None or portfolio_notional <= 0.0 or not symbols:
        return {"stressed_var": None, "stressed_es": None}

    sigma = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    stressed_corr = np.eye(len(symbols), dtype=float)
    stressed_corr[~np.eye(len(symbols), dtype=bool)] = corr_floor
    stressed_cov = np.outer(sigma, sigma) * stressed_corr
    port_var = float(weights.T @ stressed_cov @ weights)
    port_std = float(np.sqrt(max(port_var, 0.0)))
    if port_std <= 0.0:
        return {"stressed_var": None, "stressed_es": None}

    z = 1.6448536269514722
    phi_over_tail = 2.0627128075074257
    stressed_var = z * port_std * portfolio_notional
    stressed_es = phi_over_tail * port_std * portfolio_notional
    return {"stressed_var": float(stressed_var), "stressed_es": float(stressed_es)}
