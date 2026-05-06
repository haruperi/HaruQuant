"""Strategy registry for simulation backtest configs."""

from __future__ import annotations

from typing import Dict, Iterable, Type

from services.strategy.base import BaseStrategy


class StrategyRegistryError(LookupError):
    """Raised when a strategy cannot be resolved from the registry."""


StrategyClass = Type[BaseStrategy]


_STRATEGIES: Dict[str, StrategyClass] = {}
_BUILTINS_REGISTERED = False


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
    if normalized in _STRATEGIES:
        return _STRATEGIES[normalized]
    _ensure_builtin_strategies_registered()
    try:
        return _STRATEGIES[normalized]
    except KeyError as exc:
        available = ", ".join(list_strategy_names())
        raise StrategyRegistryError(
            f"unknown strategy {normalized!r}; available strategies: {available}"
        ) from exc


def list_strategy_names() -> tuple[str, ...]:
    """Return registered strategy names in stable order."""
    _ensure_builtin_strategies_registered()
    return tuple(sorted(_STRATEGIES))


def registered_strategies() -> Dict[str, StrategyClass]:
    """Return a shallow copy of the registry."""
    _ensure_builtin_strategies_registered()
    return dict(_STRATEGIES)


def register_builtin_strategies() -> None:
    """Register built-in simulation strategies."""
    for strategy_cls in _builtin_strategy_classes():
        register_strategy(strategy_cls.__name__, strategy_cls)


def _ensure_builtin_strategies_registered() -> None:
    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED:
        return
    register_builtin_strategies()
    _BUILTINS_REGISTERED = True


def _builtin_strategy_classes() -> Iterable[StrategyClass]:
    from data.strategies.pyramiding import PyramidingStrategy
    from data.strategies.rsi_averaging_pyramid import RsiAveragingPyramidStrategy
    from data.strategies.rsi_decomposing_reentry import RsiDecomposingReentryStrategy
    from data.strategies.rsi_martingale import RsiMartingaleStrategy
    from data.strategies.mtf_hedge_trail import StructureHedgeTrailStrategy
    from data.strategies.trade_decomposition import TradeDecompositionStrategy
    from data.strategies.close_breakout import CloseBreakoutStrategy
    from data.strategies.trend_following import TrendFollowingStrategy

    return (
        TrendFollowingStrategy,
        CloseBreakoutStrategy,
        RsiMartingaleStrategy,
        PyramidingStrategy,
        TradeDecompositionStrategy,
        RsiAveragingPyramidStrategy,
        StructureHedgeTrailStrategy,
        RsiDecomposingReentryStrategy,
    )
