"""Backtest database compatibility wrapper."""

from apps.sqlite import SQLiteDatabase


class BacktestDatabase(SQLiteDatabase):
    """Backtest persistence entry point (SQLite-backed)."""

    def save_result(self, backtest_result, backtest_id: int) -> int:
        """Persist a backtest result using the SQLite backtest manager."""
        return self.save_backtest_result(backtest_result, backtest_id=backtest_id)

    def load_result(self, backtest_id: int):
        """Load a backtest result using the SQLite backtest manager."""
        return self.load_backtest_result(backtest_id)


__all__ = ["BacktestDatabase"]
