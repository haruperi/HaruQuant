import pytest

from backend.data.strategies.close_breakout import CloseBreakoutStrategy
from backend.data.strategies.trend_following import TrendFollowingStrategy
from services.simulation.strategy_registry import (
    StrategyRegistryError,
    get_strategy_class,
    list_strategy_names,
    register_strategy,
    registered_strategies,
)
from services.strategy.base import BaseStrategy


class TemporaryTestStrategy(BaseStrategy):
    def on_init(self) -> None:
        return None

    def on_bar(self, data):
        return data

    def get_signal(self, data, index):
        return None


def test_get_strategy_class_resolves_builtins():
    assert get_strategy_class("TrendFollowingStrategy") is TrendFollowingStrategy
    assert get_strategy_class("CloseBreakoutStrategy") is CloseBreakoutStrategy


def test_list_strategy_names_returns_registered_names():
    names = list_strategy_names()

    assert "TrendFollowingStrategy" in names
    assert "CloseBreakoutStrategy" in names
    assert names == tuple(sorted(names))


def test_registered_strategies_returns_copy():
    registry = registered_strategies()
    registry.pop("TrendFollowingStrategy")

    assert get_strategy_class("TrendFollowingStrategy") is TrendFollowingStrategy


def test_register_strategy_adds_custom_strategy():
    register_strategy("TemporaryTestStrategy", TemporaryTestStrategy)

    assert get_strategy_class("TemporaryTestStrategy") is TemporaryTestStrategy


def test_get_strategy_class_rejects_unknown_strategy():
    with pytest.raises(StrategyRegistryError, match="unknown strategy"):
        get_strategy_class("DoesNotExist")


def test_register_strategy_rejects_non_strategy_class():
    class NotAStrategy:
        pass

    with pytest.raises(TypeError, match="BaseStrategy"):
        register_strategy("NotAStrategy", NotAStrategy)


def test_get_strategy_class_rejects_empty_name():
    with pytest.raises(StrategyRegistryError, match="non-empty"):
        get_strategy_class("")
