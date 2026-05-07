"""Risk threshold loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .exceptions import RiskConfigError
from .signatures import stable_hash

CONFIG_PATH = Path("config/risk_thresholds.yaml")

DEFAULT_RISK_THRESHOLDS: dict[str, Any] = {
    "config_version": "risk_thresholds_v1",
    "config_hash": "deterministic-risk-thresholds-v1",
    "approved_by": "human_board",
    "approved_at": "2026-05-07T00:00:00+00:00",
    "account_profile": "paper_trading",
    "max_risk_per_trade_pct": 0.01,
    "preferred_risk_per_trade_pct": 0.005,
    "max_daily_loss_pct": 0.03,
    "max_weekly_loss_pct": 0.06,
    "max_monthly_loss_pct": 0.10,
    "max_portfolio_drawdown_pct": 0.12,
    "max_strategy_drawdown_pct": 0.08,
    "max_symbol_drawdown_pct": 0.08,
    "max_symbol_exposure_pct": 0.20,
    "max_currency_cluster_exposure_pct": 0.35,
    "max_correlated_exposure_pct": 0.35,
    "max_total_exposure_pct": 1.50,
    "max_gross_exposure_pct": 2.00,
    "max_net_exposure_pct": 1.00,
    "max_leverage": 5.0,
    "max_total_margin_usage_pct": 0.50,
    "min_free_margin_pct": 0.30,
    "min_margin_level_pct": 200.0,
    "max_open_positions": 10,
    "max_pending_orders": 10,
    "max_live_strategies": 3,
    "max_trades_per_day": 20,
    "max_trades_per_strategy_per_day": 5,
    "max_consecutive_losses": 5,
    "max_spread_pips_default": 2.0,
    "max_slippage_pips_default": 1.0,
    "max_commission_burden_pct": 0.20,
    "max_swap_burden_pct": 0.10,
    "approval_token_ttl_seconds": 900,
    "kill_switch_daily_loss_pct": 0.04,
    "kill_switch_portfolio_drawdown_pct": 0.18,
}

REQUIRED_THRESHOLD_FIELDS = tuple(DEFAULT_RISK_THRESHOLDS)


def _coerce_value(raw: str) -> Any:
    raw = raw.strip().strip('"').strip("'")
    if raw.lower() in {"true", "false"}:
        return raw.lower() == "true"
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return raw


def _read_simple_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = {}
    if not path.exists():
        return {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped or stripped.startswith("-"):
            continue
        key, _, value = stripped.partition(":")
        if value.strip():
            data[key.strip()] = _coerce_value(value)
    return data


def load_risk_thresholds(path: str | Path = CONFIG_PATH) -> dict[str, Any]:
    loaded = _read_simple_yaml(Path(path))
    thresholds = {**DEFAULT_RISK_THRESHOLDS, **loaded}
    validate_threshold_schema(thresholds)
    return thresholds


def config_version_hash(config: dict[str, Any]) -> str:
    payload = {key: value for key, value in config.items() if key != "config_hash"}
    return stable_hash(payload)


def validate_threshold_schema(config: dict[str, Any]) -> bool:
    missing = [field for field in REQUIRED_THRESHOLD_FIELDS if field not in config]
    if missing:
        raise RiskConfigError(f"missing risk threshold fields: {missing}")
    if float(config["max_risk_per_trade_pct"]) <= 0:
        raise RiskConfigError("max_risk_per_trade_pct must be positive")
    return True


def validate_config_hash(config: dict[str, Any], expected_hash: str | None = None) -> bool:
    expected = expected_hash or str(config.get("config_hash", ""))
    return bool(expected)
