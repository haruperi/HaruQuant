"""Strategy registry for simulation backtest configs."""

from __future__ import annotations

from typing import Dict, Iterable, Type

from backend.data.strategies.close_breakout import CloseBreakoutStrategy
from backend.data.strategies.trend_following import TrendFollowingStrategy
from backend.services.strategy.base import BaseStrategy


class StrategyRegistryError(LookupError):
    """Raised when a strategy cannot be resolved from the registry."""


StrategyClass = Type[BaseStrategy]


_STRATEGIES: Dict[str, StrategyClass] = {}


def _normalize_name(name: str) -> str:
    normalized = str(name or "").strip()
    if not normalized:
        raise StrategyRegistryError("strategy name must be non-empty")
    return normalized


def register_strategy(name: str, strategy_cls: StrategyClass) -> None:
    """Register a strategy class by config-facing name."""
    normalized = _normalize_name(name)
    if not isinstance(strategy_cls, type) or not issubclass(strategy_cls, BaseStrategy):
        raise TypeError("strategy_cls must be a BaseStrategy subclass")
    _STRATEGIES[normalized] = strategy_cls


def get_strategy_class(name: str) -> StrategyClass:
    """Resolve a strategy class by name."""
    normalized = _normalize_name(name)
    try:
        return _STRATEGIES[normalized]
    except KeyError as exc:
        available = ", ".join(list_strategy_names())
        raise StrategyRegistryError(
            f"unknown strategy {normalized!r}; available strategies: {available}"
        ) from exc


def list_strategy_names() -> tuple[str, ...]:
    """Return registered strategy names in stable order."""
    return tuple(sorted(_STRATEGIES))


def registered_strategies() -> Dict[str, StrategyClass]:
    """Return a shallow copy of the registry."""
    return dict(_STRATEGIES)


def register_builtin_strategies() -> None:
    """Register built-in simulation strategies."""
    for strategy_cls in _builtin_strategy_classes():
        register_strategy(strategy_cls.__name__, strategy_cls)


def _builtin_strategy_classes() -> Iterable[StrategyClass]:
    return (
        TrendFollowingStrategy,
        CloseBreakoutStrategy,
    )


register_builtin_strategies()
