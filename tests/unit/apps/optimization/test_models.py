from datetime import datetime
import pytest
from pydantic import ValidationError
from apps.optimization.models import (
    ParameterRange,
    OptimizationRequest,
    OptimizationResultItem,
    WalkForwardRequest,
    MonteCarloRequest,
    PositionSizingRequest
)

class TestModels:
    def test_parameter_range(self):
        param = ParameterRange(
            name="stop_loss",
            min=10.0,
            max=50.0,
            step=5.0,
            type="int"
        )
        assert param.name == "stop_loss"
        
        with pytest.raises(ValidationError):
            ParameterRange(name="test", min=10, max=5) # min > max not explicitly validated by pydantic here but logical check, 
            # actually pydantic doesn't check min < max by default unless validator is added. 
            # But let's check basic type validation
            ParameterRange(name="test", min="invalid", max=5)

    def test_optimization_request(self):
        req = OptimizationRequest(
            strategy_id=1,
            method="grid",
            objective="sharpe",
            symbol="EURUSD",
            timeframe="H1",
            start_date="2023-01-01",
            end_date="2023-02-01",
            parameters=[
                ParameterRange(name="p1", min=1, max=10, type="int")
            ]
        )
        assert req.method == "grid"
        assert len(req.parameters) == 1

        with pytest.raises(ValidationError):
            OptimizationRequest(
                strategy_id=1,
                method="invalid", # Invalid method
                objective="sharpe",
                symbol="EURUSD",
                timeframe="H1",
                start_date="2023-01-01",
                end_date="2023-02-01",
                parameters=[]
            )

    def test_optimization_result_item(self):
        item = OptimizationResultItem(
            result_id=1,
            parameters={"p1": 5},
            score=1.5,
            rank=1,
            sharpe_ratio=2.0,
            total_return=10.0,
            max_drawdown=5.0,
            total_trades=50,
            win_rate=0.6,
            profit_factor=1.5
        )
        assert item.score == 1.5
        assert item.parameters["p1"] == 5

    def test_walk_forward_request(self):
        req = WalkForwardRequest(
            strategy_id=1,
            objective="sharpe",
            symbol="EURUSD",
            timeframe="H1",
            start_date="2023-01-01",
            end_date="2023-06-01",
            train_period=1000,
            test_period=200,
            parameters=[
                ParameterRange(name="p1", min=1, max=10, type="int")
            ]
        )
        assert req.train_period == 1000

    def test_monte_carlo_request(self):
        req = MonteCarloRequest(
            backtest_id=1,
            simulation_type="shuffle_trades",
            num_simulations=100
        )
        assert req.num_simulations == 100
        
        with pytest.raises(ValidationError):
            MonteCarloRequest(
                backtest_id=1,
                simulation_type="invalid"
            )

    def test_position_sizing_request(self):
        req = PositionSizingRequest(
            win_rate=0.5,
            reward_risk_ratio=2.0,
            risk_per_trade=0.01,
            num_trades=100
        )
        assert req.win_rate == 0.5

        with pytest.raises(ValidationError):
            PositionSizingRequest(
                win_rate=1.5, # > 1.0
                reward_risk_ratio=2.0,
                risk_per_trade=0.01,
                num_trades=100
            )
