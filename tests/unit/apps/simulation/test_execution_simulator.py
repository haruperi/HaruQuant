"""
Unit tests for order execution and fill logic.

Tests:
    - Market order fills
    - Limit order fills
    - Stop order fills
    - Slippage calculations
    - Commission calculations
    - Spread application
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from datetime import datetime

import pytest

from apps.mt5 import get_mt5_api
from apps.simulation.data import (
    AccountInfoSimulator,
    OrderInfoSimulator,
    TradeSimulator,
    SymbolInfoSimulator,
    SymbolTickSimulator,
)

mt5 = get_mt5_api()


class TestMarketOrderFills:
    """Test market order execution and fill logic."""

    def test_market_buy_fill_at_ask(self):
        """Test that market buy orders fill at ask price."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            digits=5,
            trade_contract_size=100000.0,
        )
        tick = SymbolTickSimulator(
            bid=1.10000,
            ask=1.10010,  # 1 pip spread
        )

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Market buy request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 0.0,  # 0 means use current market price
            "deviation": 10,
            "magic": 123456,
            "comment": "Test buy",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        result = client.order_send(request)

        # Should fill at ask price
        assert result["retcode"] == mt5.TRADE_RETCODE_DONE
        # Price should be ask (1.10010)
        assert result["price"] == pytest.approx(1.10010, rel=1e-6)

    def test_market_sell_fill_at_bid(self):
        """Test that market sell orders fill at bid price."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            digits=5,
            trade_contract_size=100000.0,
        )
        tick = SymbolTickSimulator(
            bid=1.10000,
            ask=1.10010,  # 1 pip spread
        )

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Market sell request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_SELL,
            "price": 0.0,
            "deviation": 10,
            "magic": 123456,
            "comment": "Test sell",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,
        }

        result = client.order_send(request)

        # Should fill at bid price
        assert result["retcode"] == mt5.TRADE_RETCODE_DONE
        # Price should be bid (1.10000)
        assert result["price"] == pytest.approx(1.10000, rel=1e-6)

    def test_market_order_creates_position(self):
        """Test that market order creates position in positions_data."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD", trade_contract_size=100000.0)
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 0.0,
        }

        result = client.order_send(request)

        assert result["retcode"] == mt5.TRADE_RETCODE_DONE
        # Position should be created
        positions = client.positions_get()
        assert len(positions) == 1
        assert positions[0].symbol == "EURUSD"
        assert positions[0].volume == 0.1
        assert positions[0].type == mt5.POSITION_TYPE_BUY

    def test_market_order_updates_account_balance(self):
        """Test that market order does NOT deduct commission on entry (applied on close)."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            trade_contract_size=100000.0,
        )
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Set commission per contract
        client._backtest_commission_per_contract = 7.0  # $7 per lot

        initial_balance = client.account_info().balance

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 1.0,  # 1 full lot
            "type": mt5.ORDER_TYPE_BUY,
            "price": 0.0,
        }

        client.order_send(request)

        # Balance should NOT change on entry (commission applied on close)
        # Only margin is locked up, not commission
        new_balance = client.account_info().balance
        assert new_balance == pytest.approx(initial_balance, rel=1e-6)


class TestLimitOrderFills:
    """Test limit order placement and fill logic."""

    def test_buy_limit_order_placement(self):
        """Test placing a buy limit order."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD", trade_contract_size=100000.0)
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Buy limit below current ask
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY_LIMIT,
            "price": 1.09900,  # Below current market
            "sl": 1.09800,
            "tp": 1.10200,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        result = client.order_send(request)

        assert result["retcode"] == mt5.TRADE_RETCODE_DONE
        # Order should be placed (not filled yet)
        orders = client.orders_get()
        assert len(orders) == 1
        assert orders[0].type == mt5.ORDER_TYPE_BUY_LIMIT
        assert orders[0].price_open == 1.09900

    def test_sell_limit_order_placement(self):
        """Test placing a sell limit order."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD", trade_contract_size=100000.0)
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Sell limit above current bid
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_SELL_LIMIT,
            "price": 1.10100,  # Above current market
            "sl": 1.10200,
            "tp": 1.09800,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        result = client.order_send(request)

        assert result["retcode"] == mt5.TRADE_RETCODE_DONE
        # Order should be placed (not filled yet)
        orders = client.orders_get()
        assert len(orders) == 1
        assert orders[0].type == mt5.ORDER_TYPE_SELL_LIMIT
        assert orders[0].price_open == 1.10100

    def test_limit_order_validation_buy_above_ask_fails(self):
        """Test that buy limit above ask is rejected."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD")
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Try to place buy limit above ask (invalid)
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY_LIMIT,
            "price": 1.10020,  # Above ask - invalid for buy limit
        }

        result = client.order_send(request)

        # Should fail validation
        assert result["retcode"] != mt5.TRADE_RETCODE_DONE
        assert len(client.orders_get()) == 0

    def test_limit_order_validation_sell_below_bid_fails(self):
        """Test that sell limit below bid is rejected."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD")
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Try to place sell limit below bid (invalid)
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_SELL_LIMIT,
            "price": 1.09990,  # Below bid - invalid for sell limit
        }

        result = client.order_send(request)

        # Should fail validation
        assert result["retcode"] != mt5.TRADE_RETCODE_DONE
        assert len(client.orders_get()) == 0


class TestStopOrderFills:
    """Test stop order placement and fill logic."""

    def test_buy_stop_order_placement(self):
        """Test placing a buy stop order."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD", trade_contract_size=100000.0)
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Buy stop above current ask
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY_STOP,
            "price": 1.10100,  # Above current market
            "sl": 1.10000,
            "tp": 1.10300,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        result = client.order_send(request)

        assert result["retcode"] == mt5.TRADE_RETCODE_DONE
        # Order should be placed (not filled yet)
        orders = client.orders_get()
        assert len(orders) == 1
        assert orders[0].type == mt5.ORDER_TYPE_BUY_STOP
        assert orders[0].price_open == 1.10100

    def test_sell_stop_order_placement(self):
        """Test placing a sell stop order."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD", trade_contract_size=100000.0)
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Sell stop below current bid
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_SELL_STOP,
            "price": 1.09900,  # Below current market
            "sl": 1.10000,
            "tp": 1.09600,
            "type_time": mt5.ORDER_TIME_GTC,
        }

        result = client.order_send(request)

        assert result["retcode"] == mt5.TRADE_RETCODE_DONE
        # Order should be placed (not filled yet)
        orders = client.orders_get()
        assert len(orders) == 1
        assert orders[0].type == mt5.ORDER_TYPE_SELL_STOP
        assert orders[0].price_open == 1.09900

    def test_stop_order_validation_buy_below_ask_fails(self):
        """Test that buy stop below ask is rejected."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD")
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Try to place buy stop below ask (invalid)
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY_STOP,
            "price": 1.10000,  # At or below ask - invalid for buy stop
        }

        result = client.order_send(request)

        # Should fail validation
        assert result["retcode"] != mt5.TRADE_RETCODE_DONE
        assert len(client.orders_get()) == 0

    def test_stop_order_validation_sell_above_bid_fails(self):
        """Test that sell stop above bid is rejected."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD")
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Try to place sell stop above bid (invalid)
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_SELL_STOP,
            "price": 1.10010,  # At or above bid - invalid for sell stop
        }

        result = client.order_send(request)

        # Should fail validation
        assert result["retcode"] != mt5.TRADE_RETCODE_DONE
        assert len(client.orders_get()) == 0


class TestSlippageCalculations:
    """Test slippage application in order execution."""

    def test_buy_order_with_slippage(self):
        """Test that buy orders apply positive slippage (worse fill)."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            digits=5,
            trade_contract_size=100000.0,
        )
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Configure 2 points slippage
        client._backtest_slippage_points = 2.0

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 0.0,
        }

        result = client.order_send(request)

        assert result["retcode"] == mt5.TRADE_RETCODE_DONE
        # Fill price should be ask + slippage
        # ask = 1.10010, slippage = 2 * 0.00001 = 0.00002
        # fill = 1.10010 + 0.00002 = 1.10012
        expected_fill = 1.10010 + (2.0 * 0.00001)
        assert result["price"] == pytest.approx(expected_fill, rel=1e-6)

    def test_sell_order_with_slippage(self):
        """Test that sell orders apply negative slippage (worse fill)."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            digits=5,
            trade_contract_size=100000.0,
        )
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Configure 2 points slippage
        client._backtest_slippage_points = 2.0

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_SELL,
            "price": 0.0,
        }

        result = client.order_send(request)

        assert result["retcode"] == mt5.TRADE_RETCODE_DONE
        # Fill price should be bid - slippage
        # bid = 1.10000, slippage = 2 * 0.00001 = 0.00002
        # fill = 1.10000 - 0.00002 = 1.09998
        expected_fill = 1.10000 - (2.0 * 0.00001)
        assert result["price"] == pytest.approx(expected_fill, rel=1e-6)

    def test_slippage_scales_with_points(self):
        """Test that slippage scales correctly with configured points."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            digits=5,
        )
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Test different slippage amounts
        slippage_tests = [1.0, 5.0, 10.0]

        for slippage_points in slippage_tests:
            client._backtest_slippage_points = slippage_points

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "EURUSD",
                "volume": 0.1,
                "type": mt5.ORDER_TYPE_BUY,
                "price": 0.0,
            }

            result = client.order_send(request)

            expected_fill = 1.10010 + (slippage_points * 0.00001)
            assert result["price"] == pytest.approx(expected_fill, rel=1e-6)

            # Close position for next test
            positions = client.positions_get()
            if positions:
                client.order_send(
                    {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": "EURUSD",
                        "volume": 0.1,
                        "type": mt5.ORDER_TYPE_SELL,
                        "position": positions[0].ticket,
                    }
                )

    def test_zero_slippage(self):
        """Test that zero slippage fills at exact market price."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            digits=5,
        )
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # No slippage configured (default 0)
        client._backtest_slippage_points = 0.0

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 0.0,
        }

        result = client.order_send(request)

        # Should fill at exact ask (no slippage)
        assert result["price"] == pytest.approx(1.10010, rel=1e-6)


class TestCommissionCalculations:
    """Test commission calculation logic."""

    def test_entry_commission_calculation(self):
        """Test commission calculation applied on position close."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            trade_contract_size=100000.0,
        )
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Set commission per lot
        client._backtest_commission_per_contract = 3.50  # $3.50 per lot round-trip

        initial_balance = client.account_info().balance

        # Open 1.0 lot position
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 1.0,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 0.0,
        }

        result = client.order_send(request)
        position_id = result["order"]

        # Balance unchanged after entry (commission applied on close)
        assert client.account_info().balance == pytest.approx(initial_balance, rel=1e-6)

        # Close position
        close_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position_id,
            "symbol": "EURUSD",
            "volume": 1.0,
            "type": mt5.ORDER_TYPE_SELL,
            "price": 0.0,
        }

        client.order_send(close_request)

        # Commission deducted on close = -$3.50
        # Assuming breakeven trade (no profit/loss), balance should decrease by commission
        new_balance = client.account_info().balance
        # Balance = initial + profit + commission
        # For breakeven: balance ≈ initial - 3.50 (commission is negative)
        assert new_balance < initial_balance  # Commission was deducted

    def test_round_trip_commission_calculation(self):
        """Test total commission for entry + exit."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            trade_contract_size=100000.0,
        )

        client = TradeSimulator(
            account_data=account, symbols_data={"EURUSD": symbol}
        )

        # Set commission per lot (this is per round trip in the calc_close_costs)
        client._backtest_commission_per_contract = 7.00  # $7 per lot total

        # Calculate close costs
        open_time = 1609459200  # 2021-01-01 00:00:00
        close_time = 1609545600  # 2021-01-02 00:00:00

        commission, fee, swap = client._calc_close_costs(
            symbol_info=symbol,
            pos_type=mt5.POSITION_TYPE_BUY,
            volume=1.0,
            open_time=open_time,
            close_time=close_time,
        )

        # Commission = -7.00 (negative because it's a cost)
        assert commission == pytest.approx(-7.00, abs=0.01)

    def test_commission_scales_with_volume(self):
        """Test that commission scales linearly with volume."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
        )

        client = TradeSimulator(
            account_data=account, symbols_data={"EURUSD": symbol}
        )

        # Set commission per lot
        client._backtest_commission_per_contract = 7.00  # $7 per lot

        volumes = [0.1, 0.5, 1.0, 2.0]
        open_time = 1609459200
        close_time = 1609545600

        for volume in volumes:
            commission, fee, swap = client._calc_close_costs(
                symbol_info=symbol,
                pos_type=mt5.POSITION_TYPE_BUY,
                volume=volume,
                open_time=open_time,
                close_time=close_time,
            )

            # Commission = volume * commission_per_lot (negative)
            expected = -volume * 7.00
            assert commission == pytest.approx(expected, abs=0.01)

    def test_swap_calculation_one_day(self):
        """Test swap calculation for one day hold."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            swap_long=-0.50,  # $0.50 per lot per day
        )

        client = TradeSimulator(
            account_data=account, symbols_data={"EURUSD": symbol}
        )

        # No commission for this test
        client._backtest_commission_per_contract = 0.0

        # Hold for 1 day
        open_time = 1609459200  # 2021-01-01 00:00:00
        close_time = 1609545600  # 2021-01-02 00:00:00 (24 hours later)

        commission, fee, swap = client._calc_close_costs(
            symbol_info=symbol,
            pos_type=mt5.POSITION_TYPE_BUY,
            volume=1.0,
            open_time=open_time,
            close_time=close_time,
        )

        # Swap = 1 day * $0.50/day * 1.0 lots = $0.50
        assert swap == pytest.approx(-0.50, abs=0.01)

    def test_swap_calculation_multiple_days(self):
        """Test swap calculation for multiple days hold."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            swap_long=-0.50,  # $0.50 per lot per day
        )

        client = TradeSimulator(
            account_data=account, symbols_data={"EURUSD": symbol}
        )

        # No commission for this test
        client._backtest_commission_per_contract = 0.0

        # Hold for 5 days
        open_time = 1609459200  # 2021-01-01 00:00:00
        close_time = 1609891200  # 2021-01-06 00:00:00 (5 days later)

        commission, fee, swap = client._calc_close_costs(
            symbol_info=symbol,
            pos_type=mt5.POSITION_TYPE_BUY,
            volume=1.0,
            open_time=open_time,
            close_time=close_time,
        )

        # Swap = 5 days * $0.50/day * 1.0 lots = $2.50
        assert swap == pytest.approx(-2.50, abs=0.01)

    def test_swap_long_vs_short(self):
        """Test that long and short positions have different swap rates."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            swap_long=-0.50,  # Pay $0.50/day for long
            swap_short=0.30,  # Earn $0.30/day for short
        )

        client = TradeSimulator(
            account_data=account, symbols_data={"EURUSD": symbol}
        )

        # No commission for this test
        client._backtest_commission_per_contract = 0.0

        open_time = 1609459200
        close_time = 1609545600  # 1 day

        # Long position
        commission_long, fee_long, swap_long = client._calc_close_costs(
            symbol_info=symbol,
            pos_type=mt5.POSITION_TYPE_BUY,
            volume=1.0,
            open_time=open_time,
            close_time=close_time,
        )

        # Short position
        commission_short, fee_short, swap_short = client._calc_close_costs(
            symbol_info=symbol,
            pos_type=mt5.POSITION_TYPE_SELL,
            volume=1.0,
            open_time=open_time,
            close_time=close_time,
        )

        assert swap_long == pytest.approx(-0.50, abs=0.01)
        assert swap_short == pytest.approx(0.30, abs=0.01)


class TestSpreadApplication:
    """Test spread application in order execution."""

    def test_spread_creates_immediate_loss(self):
        """Test that spread creates immediate loss on entry."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            spread=10,  # 10 points = 1 pip
            trade_contract_size=100000.0,
        )
        # Mid price = 1.10000
        # Spread = 10 points = 0.0001
        # Bid = 1.09995, Ask = 1.10005
        tick = SymbolTickSimulator(bid=1.09995, ask=1.10005)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Buy at ask
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 0.0,
        }

        result = client.order_send(request)
        ticket = result["order"]

        # Get position
        positions = client.positions_get()
        position = positions[0]

        # Entry at ask = 1.10005
        # Current value at bid = 1.09995
        # Immediate loss = spread = 1 pip = $1 for 0.1 lots
        # (0.10005 - 1.09995) = 0.0001 = 1 pip
        # 0.1 lots * 1 pip * $10/pip = -$1

        assert position.price_open == pytest.approx(1.10005, rel=1e-6)
        # Profit should be negative (spread loss)
        # For 0.1 lots, 1 pip = $1
        assert position.profit <= 0

    def test_spread_difference_buy_vs_sell(self):
        """Test that spread affects buy and sell differently."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(
            symbol="EURUSD",
            point=0.00001,
            spread=20,  # 20 points = 2 pips
            trade_contract_size=100000.0,
        )
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10020)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        # Buy at ask
        buy_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
            "price": 0.0,
        }

        buy_result = client.order_send(buy_request)
        assert buy_result["price"] == pytest.approx(1.10020, rel=1e-6)

        # Close buy position
        client.order_send(
            {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "EURUSD",
                "volume": 0.1,
                "type": mt5.ORDER_TYPE_SELL,
                "position": buy_result["order"],
            }
        )

        # Sell at bid
        sell_request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_SELL,
            "price": 0.0,
        }

        sell_result = client.order_send(sell_request)
        assert sell_result["price"] == pytest.approx(1.10000, rel=1e-6)

        # Spread = ask - bid = 1.10020 - 1.10000 = 0.00020 = 2 pips
        spread = buy_result["price"] - sell_result["price"]
        assert spread == pytest.approx(0.00020, rel=1e-6)

    def test_wide_spread_high_cost(self):
        """Test that wider spreads create higher costs."""
        account = AccountInfoSimulator(balance=10000.0)

        # Test different spread widths
        spreads = [10, 20, 50]  # 1 pip, 2 pips, 5 pips

        for spread_points in spreads:
            symbol = SymbolInfoSimulator(
                symbol="EURUSD",
                point=0.00001,
                spread=spread_points,
            )

            spread_price = spread_points * 0.00001
            mid_price = 1.10000
            bid = mid_price - (spread_price / 2)
            ask = mid_price + (spread_price / 2)

            tick = SymbolTickSimulator(bid=bid, ask=ask)

            client = TradeSimulator(
                account_data=account,
                symbols_data={"EURUSD": symbol},
                ticks_data={"EURUSD": tick},
            )

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "EURUSD",
                "volume": 0.1,
                "type": mt5.ORDER_TYPE_BUY,
                "price": 0.0,
            }

            result = client.order_send(request)

            # Spread cost = (ask - bid)
            expected_spread = spread_points * 0.00001
            actual_spread = result["price"] - bid
            assert actual_spread == pytest.approx(expected_spread, rel=1e-6)


class TestOrderValidation:
    """Test order validation logic."""

    def test_invalid_volume_zero(self):
        """Test that zero volume is rejected."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD")
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "EURUSD",
            "volume": 0.0,  # Invalid: zero volume
            "type": mt5.ORDER_TYPE_BUY,
        }

        result = client.order_send(request)

        assert result["retcode"] != mt5.TRADE_RETCODE_DONE

    def test_invalid_symbol(self):
        """Test that invalid symbol is rejected."""
        account = AccountInfoSimulator(balance=10000.0)
        symbol = SymbolInfoSimulator(symbol="EURUSD")
        tick = SymbolTickSimulator(bid=1.10000, ask=1.10010)

        client = TradeSimulator(
            account_data=account,
            symbols_data={"EURUSD": symbol},
            ticks_data={"EURUSD": tick},
        )

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "INVALID_SYMBOL",  # Not in symbols_data
            "volume": 0.1,
            "type": mt5.ORDER_TYPE_BUY,
        }

        result = client.order_send(request)

        assert result["retcode"] != mt5.TRADE_RETCODE_DONE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

