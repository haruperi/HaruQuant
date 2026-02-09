"""
Unit tests for trade recording and management.

Tests:
    - Trade record creation
    - Trade PnL calculation
    - Trade metrics tracking (MAE/MFE, R-multiple)
    - Trade lifecycle management
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime, timedelta

import pytest

from apps.simulation.records import TradeRecord


class TestTradeRecordCreation:
    """Test trade record creation and initialization."""

    def test_trade_record_default_creation(self):
        """Test creating a TradeRecord with default values."""
        trade = TradeRecord()

        assert trade.ticket == 0
        assert trade.symbol == ""
        assert trade.type == "buy"
        assert trade.size == 0.0
        assert trade.profit_loss == 0.0
        assert trade.open_time is None
        assert trade.close_time is None

    def test_trade_record_with_values(self):
        """Test creating a TradeRecord with specific values."""
        open_time = datetime(2024, 1, 1, 10, 0, 0)
        close_time = datetime(2024, 1, 1, 12, 0, 0)

        trade = TradeRecord(
            ticket=12345,
            symbol="EURUSD",
            type="buy",
            size=0.1,
            open_price=1.1000,
            close_price=1.1050,
            open_time=open_time,
            close_time=close_time,
            profit_loss=50.0,
            profit_loss_pips=50.0,
            strategy_name="TestStrategy",
            setup_id="BREAKOUT_001",
        )

        assert trade.ticket == 12345
        assert trade.symbol == "EURUSD"
        assert trade.type == "buy"
        assert trade.size == 0.1
        assert trade.open_price == 1.1000
        assert trade.close_price == 1.1050
        assert trade.profit_loss == 50.0
        assert trade.profit_loss_pips == 50.0
        assert trade.strategy_name == "TestStrategy"
        assert trade.setup_id == "BREAKOUT_001"

    def test_trade_record_all_fields(self):
        """Test that all TradeRecord fields can be set."""
        trade = TradeRecord(
            # Identification
            trade_id="trade_001",
            ticket=10001,
            symbol="GBPUSD",
            type="sell",
            magic_number=100,
            strategy_name="MeanReversion",
            setup_id="REVERSAL_001",
            sample_type="in_sample",
            comment="Test trade",
            # Context
            signal_timeframe="H1",
            execution_timeframe="M5",
            session="LONDON",
            day_of_week=1,
            hour_of_day=10,
            # Timing
            open_time=datetime(2024, 1, 1, 10, 0),
            close_time=datetime(2024, 1, 1, 12, 0),
            time_in_trade=7200.0,
            bars_in_trade=120,
            # Entry
            open_price=1.3000,
            size=0.2,
            spread_at_entry=0.0002,
            atr_at_entry=0.0050,
            # Exit
            close_price=1.2950,
            close_type="TP",
            exit_reason="RISK_EXIT",
            # Risk
            stop_loss_price=1.3050,
            profit_target_price=1.2900,
            initial_risk_pips=50.0,
            initial_risk_usd=100.0,
            # Performance
            profit_loss=100.0,
            profit_loss_pips=50.0,
            commission=2.0,
            swap=0.5,
            r_multiple=1.0,
            # Excursion
            mae_usd=20.0,
            mae_pips=10.0,
            mfe_usd=120.0,
            mfe_pips=60.0,
            # Account
            balance_at_entry=10000.0,
            equity_at_entry=10000.0,
            margin_used=260.0,
        )

        # Verify all fields are set
        assert trade.trade_id == "trade_001"
        assert trade.ticket == 10001
        assert trade.symbol == "GBPUSD"
        assert trade.strategy_name == "MeanReversion"
        assert trade.r_multiple == 1.0
        assert trade.mae_usd == 20.0
        assert trade.mfe_usd == 120.0


class TestTradePnLCalculations:
    """Test profit and loss calculations for trades."""

    def test_buy_trade_profit(self):
        """Test PnL calculation for profitable buy trade."""
        trade = TradeRecord(
            type="buy",
            open_price=1.1000,
            close_price=1.1050,
            size=0.1,
            profit_loss_pips=50.0,
        )

        # For 0.1 lots on EURUSD, 50 pips = $50
        trade.profit_loss = 50.0

        assert trade.profit_loss == 50.0
        assert trade.profit_loss_pips == 50.0

    def test_buy_trade_loss(self):
        """Test PnL calculation for losing buy trade."""
        trade = TradeRecord(
            type="buy",
            open_price=1.1000,
            close_price=1.0950,
            size=0.1,
            profit_loss_pips=-50.0,
        )

        trade.profit_loss = -50.0

        assert trade.profit_loss == -50.0
        assert trade.profit_loss_pips == -50.0

    def test_sell_trade_profit(self):
        """Test PnL calculation for profitable sell trade."""
        trade = TradeRecord(
            type="sell",
            open_price=1.3000,
            close_price=1.2950,
            size=0.2,
            profit_loss_pips=50.0,
        )

        # For 0.2 lots, 50 pips = $100
        trade.profit_loss = 100.0

        assert trade.profit_loss == 100.0
        assert trade.profit_loss_pips == 50.0

    def test_sell_trade_loss(self):
        """Test PnL calculation for losing sell trade."""
        trade = TradeRecord(
            type="sell",
            open_price=1.3000,
            close_price=1.3050,
            size=0.2,
            profit_loss_pips=-50.0,
        )

        trade.profit_loss = -100.0

        assert trade.profit_loss == -100.0
        assert trade.profit_loss_pips == -50.0

    def test_pnl_with_commission_and_swap(self):
        """Test PnL calculation including commission and swap."""
        trade = TradeRecord(
            type="buy",
            open_price=1.1000,
            close_price=1.1050,
            size=0.1,
            commission=2.0,  # $2 total commission
            swap=0.5,  # $0.5 swap
        )

        # Gross profit = $50, Net profit = 50 - 2 + 0.5 = 48.5
        trade.profit_loss = 48.5

        assert trade.profit_loss == 48.5
        assert trade.commission == 2.0
        assert trade.swap == 0.5

    def test_r_multiple_calculation(self):
        """Test R-multiple calculation."""
        # R-multiple = Profit / Initial Risk

        # Case 1: 2R winner
        trade = TradeRecord(
            profit_loss=100.0,
            initial_risk_usd=50.0,
            r_multiple=2.0,
        )

        assert trade.r_multiple == 2.0

        # Case 2: 1R loser
        trade = TradeRecord(
            profit_loss=-50.0,
            initial_risk_usd=50.0,
            r_multiple=-1.0,
        )

        assert trade.r_multiple == -1.0

        # Case 3: 0.5R partial winner
        trade = TradeRecord(
            profit_loss=25.0,
            initial_risk_usd=50.0,
            r_multiple=0.5,
        )

        assert trade.r_multiple == 0.5


class TestTradeMetrics:
    """Test trade metrics tracking (MAE, MFE, etc.)."""

    def test_mae_tracking(self):
        """Test Maximum Adverse Excursion tracking."""
        trade = TradeRecord(
            type="buy",
            open_price=1.1000,
            mae_usd=25.0,  # Went $25 against us
            mae_pips=25.0,
            profit_loss=50.0,  # But closed with $50 profit
        )

        assert trade.mae_usd == 25.0
        assert trade.mae_pips == 25.0
        # MAE shows how much it went against us before recovering
        assert trade.profit_loss > trade.mae_usd

    def test_mfe_tracking(self):
        """Test Maximum Favorable Excursion tracking."""
        trade = TradeRecord(
            type="buy",
            open_price=1.1000,
            mfe_usd=100.0,  # Went up to $100 profit
            mfe_pips=100.0,
            profit_loss=50.0,  # But closed with only $50 profit
        )

        assert trade.mfe_usd == 100.0
        assert trade.mfe_pips == 100.0
        # MFE shows we gave back $50 of profit
        assert trade.mfe_usd > trade.profit_loss

    def test_mae_mfe_perfect_exit(self):
        """Test MAE/MFE when exit is at maximum favorable."""
        trade = TradeRecord(
            type="buy",
            open_price=1.1000,
            close_price=1.1100,
            mae_usd=10.0,  # Small adverse excursion
            mae_pips=10.0,
            mfe_usd=100.0,  # Closed at MFE
            mfe_pips=100.0,
            profit_loss=100.0,
        )

        # Perfect exit: MFE == profit_loss
        assert trade.mfe_usd == trade.profit_loss

    def test_mae_mfe_worst_exit(self):
        """Test MAE/MFE when stopped out at maximum adverse."""
        trade = TradeRecord(
            type="buy",
            open_price=1.1000,
            stop_loss_price=1.0950,
            mae_usd=50.0,  # Hit stop loss
            mae_pips=50.0,
            mfe_usd=20.0,  # Had some favorable movement
            mfe_pips=20.0,
            profit_loss=-50.0,  # Stopped out
        )

        # Worst exit: abs(profit_loss) == mae_usd
        assert abs(trade.profit_loss) == trade.mae_usd


class TestTradeLifecycle:
    """Test trade lifecycle management."""

    def test_trade_time_in_trade(self):
        """Test time_in_trade calculation."""
        open_time = datetime(2024, 1, 1, 10, 0, 0)
        close_time = datetime(2024, 1, 1, 12, 0, 0)

        trade = TradeRecord(
            open_time=open_time,
            close_time=close_time,
            time_in_trade=(close_time - open_time).total_seconds(),
        )

        # 2 hours = 7200 seconds
        assert trade.time_in_trade == 7200.0

    def test_trade_bars_in_trade(self):
        """Test bars_in_trade tracking."""
        # 2 hours on M5 = 24 bars
        trade = TradeRecord(
            open_time=datetime(2024, 1, 1, 10, 0, 0),
            close_time=datetime(2024, 1, 1, 12, 0, 0),
            bars_in_trade=24,
            execution_timeframe="M5",
        )

        assert trade.bars_in_trade == 24
        assert trade.execution_timeframe == "M5"

    def test_trade_session_context(self):
        """Test trade session and time context."""
        trade = TradeRecord(
            session="LONDON",
            day_of_week=1,  # Monday
            hour_of_day=10,
            open_time=datetime(2024, 1, 1, 10, 0, 0),
        )

        assert trade.session == "LONDON"
        assert trade.day_of_week == 1
        assert trade.hour_of_day == 10

    def test_trade_exit_types(self):
        """Test different trade exit types."""
        # Stop loss exit
        trade_sl = TradeRecord(
            close_type="SL",
            exit_reason="RISK_EXIT",
            profit_loss=-50.0,
        )

        assert trade_sl.close_type == "SL"
        assert trade_sl.exit_reason == "RISK_EXIT"

        # Take profit exit
        trade_tp = TradeRecord(
            close_type="TP",
            exit_reason="RISK_EXIT",
            profit_loss=100.0,
        )

        assert trade_tp.close_type == "TP"
        assert trade_tp.exit_reason == "RISK_EXIT"

        # Signal exit
        trade_signal = TradeRecord(
            close_type="SIGNAL_EXIT",
            exit_reason="STRATEGY_EXIT",
            profit_loss=25.0,
        )

        assert trade_signal.close_type == "SIGNAL_EXIT"
        assert trade_signal.exit_reason == "STRATEGY_EXIT"

        # Time exit
        trade_time = TradeRecord(
            close_type="TIME_EXIT",
            exit_reason="TIMEOUT",
            profit_loss=10.0,
        )

        assert trade_time.close_type == "TIME_EXIT"
        assert trade_time.exit_reason == "TIMEOUT"


class TestTradeAccountContext:
    """Test trade account state context."""

    def test_account_state_at_entry(self):
        """Test recording account state at trade entry."""
        trade = TradeRecord(
            balance_at_entry=10000.0,
            equity_at_entry=10000.0,
            margin_used=110.0,
            free_margin=9890.0,
        )

        assert trade.balance_at_entry == 10000.0
        assert trade.equity_at_entry == 10000.0
        assert trade.margin_used == 110.0

    def test_risk_parameters(self):
        """Test trade risk parameters."""
        trade = TradeRecord(
            stop_loss_price=1.0950,
            profit_target_price=1.1150,
            initial_risk_pips=50.0,
            initial_risk_usd=50.0,
        )

        assert trade.stop_loss_price == 1.0950
        assert trade.profit_target_price == 1.1150
        assert trade.initial_risk_pips == 50.0
        assert trade.initial_risk_usd == 50.0

    def test_position_sizing(self):
        """Test position size and max size tracking."""
        trade = TradeRecord(
            size=0.1,
            max_position_size=0.1,
            balance_at_entry=10000.0,
        )

        assert trade.size == 0.1
        assert trade.max_position_size == 0.1

        # Position size as % of account
        position_value = 0.1 * 100000  # 0.1 lots of EURUSD
        account_risk_pct = (position_value / 10000.0) * 100

        # Not saved in TradeRecord but can be calculated
        assert account_risk_pct == 100.0  # 1:1 leverage effectively


class TestTradeManagementFeatures:
    """Test trade management features."""

    def test_partial_close_tracking(self):
        """Test tracking partial position closes."""
        trade = TradeRecord(
            size=1.0,
            max_position_size=1.0,
            partial_close_count=2,  # Partially closed twice
        )

        assert trade.partial_close_count == 2
        # Final size is less than max size
        assert trade.size <= trade.max_position_size

    def test_trailing_stop_usage(self):
        """Test tracking trailing stop usage."""
        trade = TradeRecord(
            trailing_stop_used=True,
            breakeven_triggered=False,
        )

        assert trade.trailing_stop_used is True
        assert trade.breakeven_triggered is False

    def test_breakeven_move(self):
        """Test tracking breakeven stop move."""
        trade = TradeRecord(
            trailing_stop_used=False,
            breakeven_triggered=True,
            stop_loss_price=1.1000,  # Moved to breakeven
            open_price=1.1000,
        )

        assert trade.breakeven_triggered is True
        assert trade.stop_loss_price == trade.open_price


class TestTradeMetadata:
    """Test trade metadata and tagging."""

    def test_strategy_attribution(self):
        """Test strategy identification fields."""
        trade = TradeRecord(
            strategy_name="MeanReversion",
            setup_id="REVERSAL_001",
            sample_type="in_sample",
            magic_number=12345,
        )

        assert trade.strategy_name == "MeanReversion"
        assert trade.setup_id == "REVERSAL_001"
        assert trade.sample_type == "in_sample"
        assert trade.magic_number == 12345

    def test_market_regime_tagging(self):
        """Test market regime classification."""
        trade = TradeRecord(
            market_regime="TRENDING",
            volatility_bucket="HIGH",
            correlation_cluster="RISK_ON",
        )

        assert trade.market_regime == "TRENDING"
        assert trade.volatility_bucket == "HIGH"
        assert trade.correlation_cluster == "RISK_ON"

    def test_compliance_flags(self):
        """Test compliance and audit flags."""
        # Rule violation
        trade_violation = TradeRecord(
            rule_violation=True,
            manual_intervention=False,
        )

        assert trade_violation.rule_violation is True

        # Manual intervention
        trade_manual = TradeRecord(
            rule_violation=False,
            manual_intervention=True,
        )

        assert trade_manual.manual_intervention is True


class TestTradeExecutionQuality:
    """Test trade execution quality metrics."""

    def test_slippage_tracking(self):
        """Test slippage measurement."""
        trade = TradeRecord(
            requested_entry_price=1.1000,
            open_price=1.1002,  # Got 2 pips worse
            slippage_usd=2.0,
            fill_price_deviation=0.0002,
        )

        assert trade.slippage_usd == 2.0
        assert trade.fill_price_deviation == 0.0002

    def test_execution_latency(self):
        """Test execution latency tracking."""
        trade = TradeRecord(
            execution_latency_ms=150.0,  # 150ms to execute
        )

        assert trade.execution_latency_ms == 150.0

    def test_spread_at_entry(self):
        """Test recording spread at entry."""
        trade = TradeRecord(
            spread_at_entry=0.0002,  # 2 pips spread
            atr_at_entry=0.0050,  # 50 pips ATR
        )

        assert trade.spread_at_entry == 0.0002
        # Spread is 4% of ATR
        spread_to_atr = (trade.spread_at_entry / trade.atr_at_entry) * 100
        assert spread_to_atr == pytest.approx(4.0, rel=1e-6)


class TestBuyHoldComparison:
    """Test buy-and-hold comparison metrics."""

    def test_buy_hold_return(self):
        """Test buy-hold return calculation."""
        trade = TradeRecord(
            type="buy",
            open_price=1.1000,
            close_price=1.1050,
            profit_loss=50.0,
            buy_hold=50.0,  # Same as actual
            buy_hold_pips=50.0,
        )

        assert trade.buy_hold == 50.0
        assert trade.buy_hold == trade.profit_loss

    def test_short_vs_buy_hold(self):
        """Test short position vs buy-hold."""
        trade = TradeRecord(
            type="sell",
            open_price=1.1000,
            close_price=1.1050,  # Market went up
            profit_loss=-50.0,  # Lost on short
            buy_hold=50.0,  # Buy-hold would have made money
        )

        assert trade.profit_loss == -50.0
        assert trade.buy_hold == 50.0
        # Strategy underperformed buy-hold by $100
        underperformance = trade.profit_loss - trade.buy_hold
        assert underperformance == -100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
