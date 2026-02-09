
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import asdict
from apps.simulation.data import (
    AccountInfoSimulator,
    SymbolTickSimulator,
    SymbolInfoSimulator,
    TradeRecordSimulator,
    DealInfoSimulator,
    OrderInfoSimulator,
    HistoryOrderInfoSimulator,
    PositionInfoSimulator,
    TerminalInfoSimulator,
    SimulatorClient,
    _get_mt5_val,
    _get_mt5_symbol_val
)
from apps.mt5 import get_mt5_api

# Mock mt5 api for _get_mt5_val and _get_mt5_symbol_val tests
@pytest.fixture
def mock_mt5():
    with patch("apps.simulation.data.mt5") as mock:
        yield mock

def test_get_mt5_val(mock_mt5):
    mock_mt5.account_info.return_value = MagicMock(leverage=500)
    assert _get_mt5_val("leverage", 100) == 500
    
    mock_mt5.account_info.return_value = None
    assert _get_mt5_val("leverage", 100) == 100
    
    mock_mt5.account_info.side_effect = Exception("API Error")
    assert _get_mt5_val("leverage", 100) == 100

def test_get_mt5_symbol_val(mock_mt5):
    mock_mt5.symbol_info.return_value = MagicMock(digits=5)
    assert _get_mt5_symbol_val("EURUSD", "digits", 2) == 5
    
    mock_mt5.symbol_info.return_value = None
    assert _get_mt5_symbol_val("EURUSD", "digits", 2) == 2

    mock_mt5.symbol_info.side_effect = Exception("API Error")
    assert _get_mt5_symbol_val("EURUSD", "digits", 2) == 2

def test_account_info_simulator_defaults():
    with patch("apps.simulation.data._get_mt5_val", return_value="USD"):
        account = AccountInfoSimulator()
        assert account.balance == 10000
        assert isinstance(account._asdict(), dict)

def test_account_info_simulator_from_mt5(mock_mt5):
    mock_info = MagicMock()
    mock_info._asdict.return_value = {"login": 999, "balance": 5000.0}
    mock_mt5.account_info.return_value = mock_info
    
    account = AccountInfoSimulator.from_mt5_account()
    assert account.login == 999
    assert account.balance == 5000.0

    mock_mt5.account_info.return_value = None
    account = AccountInfoSimulator.from_mt5_account()
    assert account.balance == 10000 # Default

def test_symbol_tick_simulator():
    tick = SymbolTickSimulator()
    assert tick.bid == 0.0
    assert isinstance(tick._asdict(), dict)

def test_symbol_info_simulator_defaults():
    with patch("apps.simulation.data._get_mt5_symbol_val", return_value=5):
        symbol = SymbolInfoSimulator()
        assert symbol.symbol == "EURUSD"
        assert isinstance(symbol._asdict(), dict)

def test_symbol_info_simulator_from_mt5(mock_mt5):
    mock_info = MagicMock()
    mock_info._asdict.return_value = {"symbol": "GBPUSD", "digits": 4}
    mock_mt5.symbol_info.return_value = mock_info
    
    symbol = SymbolInfoSimulator.from_mt5_symbol("GBPUSD")
    assert symbol.symbol == "GBPUSD"
    assert symbol.digits == 4

    mock_mt5.symbol_info.return_value = None
    symbol = SymbolInfoSimulator.from_mt5_symbol("JPYUSD")
    assert symbol.symbol == "JPYUSD"

def test_trade_record_simulators():
    trade = TradeRecordSimulator()
    assert trade.ticket == 0
    assert isinstance(trade._asdict(), dict)
    
    deal = DealInfoSimulator()
    assert deal.commission == 0.0
    
    order = OrderInfoSimulator()
    assert order.state == 0
    
    history = HistoryOrderInfoSimulator()
    assert history.time_done == 0
    
    position = PositionInfoSimulator(ticket=123)
    data = position._asdict()
    assert data["id"] == 123

def test_terminal_info_simulator():
    term = TerminalInfoSimulator()
    assert term.trade_allowed is True
    assert isinstance(term._asdict(), dict)

class TestSimulatorClient:
    @pytest.fixture
    def client(self):
        symbols = {
            "EURUSD": SymbolInfoSimulator(symbol="EURUSD", point=0.00001, trade_stops_level=10),
        }
        ticks = {
            "EURUSD": SymbolTickSimulator(bid=1.1000, ask=1.1002)
        }
        return SimulatorClient(symbols_data=symbols, ticks_data=ticks)

    def test_initialization(self, client):
        assert client.version() == (500, 2980, "25 Mar 2026")
        assert isinstance(client.account_info(), AccountInfoSimulator)
        assert isinstance(client.terminal_info(), TerminalInfoSimulator)
        assert client.symbol_info("EURUSD").symbol == "EURUSD"
        assert client.symbol_info_tick("EURUSD").bid == 1.1000

    def test_symbol_select(self, client):
        assert client.symbol_select("EURUSD", True) is True
        assert client.symbol_select("INVALID", True) is False

    def test_order_check(self, client):
        res = client.order_check({})
        assert res["retcode"] == 10009
        assert res["comment"] == "Simulated check"

    def test_order_send_validation_failures(self, client):
        # Missing action
        res = client.order_send({})
        assert res["retcode"] == 10013
        
        # Trade disabled
        client._terminal_data.trade_allowed = False
        res = client.order_send({"action": 1}) # TRADE_ACTION_DEAL
        assert res["retcode"] == 10017
        client._terminal_data.trade_allowed = True

        # Missing symbol
        res = client.order_send({"action": 5, "type": 0}) # Pending
        assert res["retcode"] == 10013 # Missing symbol

    def test_order_send_stops_validation(self, client):
        # Basic pending order test
        res = client.order_send({
            "action": 5, # PENDING
            "symbol": "EURUSD",
            "type": 2, # BUY_LIMIT
            "volume": 0.1,
            "price": 1.0500,
        })
        # Just verify it returns a dict with retcode
        assert "retcode" in res

    def test_archive_order(self, client):
        order = OrderInfoSimulator(ticket=100, time=1000)
        client._archive_order(order, state=1, done_time=2000)
        history = client._history_orders_data[100]
        assert history.state == 1
        assert history.time_done == 2000

    def test_calc_close_costs(self, client):
        symbol = client.symbol_info("EURUSD")
        symbol.swap_mode = 1 # Points
        symbol.swap_long = -1.0
        symbol.swap_short = -1.0
        symbol.swap_rollover3days = 3 # Wednesday
        
        # 1 day difference
        comm, fee, swap = client._calc_close_costs(
            symbol, 0, 1.0, 1000000, 1000000 + 86400
        )
        assert comm == 0.0
        assert fee == 0.0
        # Swap calculation includes rollover logic
        assert swap < 0 # Negative swap

