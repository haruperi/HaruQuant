import asyncio
from unittest.mock import MagicMock, patch, ANY
import pytest
from datetime import datetime
from apps.optimization.core import run_optimization_task, run_walk_forward_task, _parse_request_date
from apps.optimization.models import OptimizationRequest, WalkForwardRequest, ParameterRange

class TestCoreHelpers:
    def test_parse_request_date(self):
        assert _parse_request_date(None) is None
        dt = datetime(2023, 1, 1)
        assert _parse_request_date(dt) == dt
        assert _parse_request_date("2023-01-01T00:00:00") == dt
        
        with pytest.raises(ValueError):
            _parse_request_date(123)

@pytest.mark.asyncio
class TestOptimizationTask:
    @pytest.fixture
    def mock_db(self):
        with patch("apps.optimization.core.DatabaseManager") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_storage(self):
        with patch("apps.optimization.core.StrategyStorage") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_mt5(self):
        with patch("apps.mt5.client.MT5Client") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_user_manager(self):
        with patch("apps.sqlite.users.UserManager") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_backtest_db(self):
        # Patching the imported BacktestDatabase (which is Any in core.py but likely used)
        # Actually core.py has `BacktestDatabase = Any` so it might not be instantiated
        # But it does `backtest_db = BacktestDatabase()` on line 69
        # Wait, line 69 is `backtest_db = BacktestDatabase()` where BacktestDatabase is assigned Any?
        # That would fail at runtime if it's just `Any`.
        # Ah, looking at imports in core.py:
        # `from apps.backtest.persistence import BacktestDatabase` is commented out?
        # and replaced with `BacktestDatabase = Any`.
        # If so, `backtest_db = BacktestDatabase()` might raise TypeError if Any is not callable like that or return Any.
        # But let's assume it's mocked or works.
        # I'll patch the name in core.py specifically.
        with patch("apps.optimization.core.BacktestDatabase") as mock:
            yield mock.return_value

    @pytest.fixture
    def valid_request(self):
        return OptimizationRequest(
            strategy_id=1,
            method="grid",
            objective="sharpe",
            symbol="EURUSD",
            timeframe="H1",
            start_date="2023-01-01",
            end_date="2023-02-01",
            parameters=[
                ParameterRange(name="p1", min=1, max=10, type="int")
            ],
            data_source="mt5"
        )

    async def test_run_optimization_metadata_error(self, mock_db, valid_request):
        # Strategy not found
        mock_db.get_strategy.return_value = None
        
        with pytest.raises(ValueError, match="Strategy with id 1 not found"):
            await run_optimization_task(1, 1, 1, valid_request)
            
        mock_db.update_optimization_status.assert_called_with(1, "failed", completed_at=ANY)

    async def test_run_optimization_success_grid(
        self, mock_db, mock_storage, mock_mt5, mock_user_manager, mock_backtest_db, valid_request
    ):
        # Setup mocks
        mock_db.get_strategy.return_value = {"name": "TestStrat", "active_version": "1.0.0"}
        mock_db.get_user.return_value = {"username": "user"}
        mock_storage.load_strategy_class.return_value = MagicMock()
        mock_storage.get_strategy_path.return_value = "path/to/strat.py"
        
        # Mock MT5 credentials and connection
        mock_user_manager.get_mt5_credentials.return_value = {
            "login": "123", "password": "pass", "server": "server", "path": "path"
        }
        mock_mt5.connect.return_value = True
        
        # Mock data
        mock_df = MagicMock()
        mock_df.empty = False
        mock_mt5.get_bars.return_value = mock_df
        
        with patch("apps.optimization.core.DataValidator.prepare_data", return_value=mock_df), \
             patch("apps.optimization.core.grid_search") as mock_grid:
            
            # Setup grid search result
            mock_summary = MagicMock()
            mock_summary.all_results = [
                MagicMock(
                    parameters={"p1": 5}, 
                    score=1.5, 
                    rank=1,
                    result=MagicMock(total_trades=10, win_rate=0.6, max_drawdown_pct=-5.0),
                    metrics={"profit_factor": 1.5, "sharpe_ratio": 2.0}
                )
            ]
            mock_summary.completed = 1
            mock_summary.best_score = 1.5
            mock_summary.best_params = {"p1": 5}
            mock_grid.return_value = mock_summary
            
            await run_optimization_task(1, 1, 1, valid_request)
            
            # Verify status update
            mock_db.update_optimization_status.assert_called_with(
                optimization_id=1,
                status="completed",
                completed_combinations=1,
                best_backtest_id=ANY,
                best_score=1.5,
                best_parameters={"p1": 5},
                completed_at=ANY
            )
            
            # Verify results saved
            mock_db.save_optimization_results.assert_called_once()


@pytest.mark.asyncio
class TestWalkForwardTask:
    @pytest.fixture
    def mock_db(self):
        with patch("apps.optimization.core.DatabaseManager") as mock:
            yield mock.return_value

    @pytest.fixture
    def mock_storage(self):
        with patch("apps.optimization.core.StrategyStorage") as mock:
            yield mock.return_value
            
    @pytest.fixture
    def valid_request(self):
        return WalkForwardRequest(
            strategy_id=1,
            objective="sharpe",
            symbol="EURUSD",
            timeframe="H1",
            start_date="2023-01-01",
            end_date="2023-06-01",
            train_period=1000,
            test_period=200,
            parameters=[
                ParameterRange(name="p1", min=1, max=10, type="int", step=1)
            ],
            data_source="dukascopy"
        )

    async def test_run_walk_forward_success(
        self, mock_db, mock_storage, valid_request
    ):
        mock_db.get_strategy.return_value = {"name": "TestStrat", "active_version": "1.0.0"}
        mock_db.get_user.return_value = {"username": "user"}
        mock_storage.load_strategy_class.return_value = MagicMock()
        
        # Mock Load Dukascopy
        with patch("apps.optimization.core.load_dukascopy") as mock_load, \
             patch("apps.optimization.core.walk_forward") as mock_wf:
            
            mock_df = MagicMock()
            mock_df.empty = False
            mock_load.return_value = mock_df
            
            await run_walk_forward_task(1, 1, 1, valid_request)
            
            mock_wf.assert_called_once()
            mock_db.update_optimization_status.assert_called_with(
                1, "completed", completed_at=ANY
            )
