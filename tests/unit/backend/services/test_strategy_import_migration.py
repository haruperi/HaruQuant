from __future__ import annotations

from scripts.tools.migrate_strategy_imports_to_agentic_paths import (
    has_legacy_apps_import,
    migrate_strategy_imports,
)


def test_migrate_strategy_imports_rewrites_legacy_apps_paths() -> None:
    code = """
from apps.strategy import BaseStrategy
from apps.strategy.base import SignalDict
from apps.indicator import sma, rsi
from apps.utils.logger import logger
from apps.trading import PositionType
from apps.trade import PositionTyp
"""

    migrated = migrate_strategy_imports(code)

    assert "apps." not in migrated
    assert "from haruquant.strategy import BaseStrategy" in migrated
    assert "from haruquant.strategy import SignalDict" in migrated
    assert "from haruquant.indicator import sma, rsi" in migrated
    assert "from haruquant.utils import logger" in migrated
    assert "from haruquant.strategy import PositionType" in migrated
    assert "from haruquant.strategy import PositionTyp" in migrated
    assert has_legacy_apps_import(migrated) is False


def test_migrate_strategy_imports_preserves_strategy_alias() -> None:
    code = """
from apps.strategy import Strategy


class Demo(Strategy):
    pass
"""

    migrated = migrate_strategy_imports(code)

    assert "from haruquant.strategy import BaseStrategy as Strategy" in migrated
    assert has_legacy_apps_import(migrated) is False

