import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import pandas as pd
import numpy as np
from apps.mt5.trade import Trade

# Mock the MT5 API
@pytest.fixture
def mock_mt5():
    with patch('apps.mt5.trade.mt5') as mocked:
        # Define common constants using distinct integer values
        mocked.TRADE_RETCODE_DONE = 10009
        mocked.TRADE_RETCODE_PLACED = 10008
        mocked.TRADE_RETCODE_REQUOTE = 10004
        mocked.TRADE_RETCODE_PRICE_OFF = 10006
        
        mocked.ORDER_FILLING_FOK = 1
        mocked.ORDER_FILLING_IOC = 2
        mocked.ORDER_FILLING_RETURN = 4
        
        mocked.TRADE_ACTION_DEAL = 1
        mocked.TRADE_ACTION_PENDING = 5
        mocked.TRADE_ACTION_MODIFY = 6
        mocked.TRADE_ACTION_REMOVE = 7
        mocked.TRADE_ACTION_SLTP = 11
        
        mocked.ORDER_TYPE_BUY = 0
        mocked.ORDER_TYPE_SELL = 1
        mocked.ORDER_TYPE_BUY_LIMIT = 2
        mocked.ORDER_TYPE_SELL_LIMIT = 3
        mocked.ORDER_TYPE_BUY_STOP = 4
        mocked.ORDER_TYPE_SELL_STOP = 5
        mocked.ORDER_TYPE_BUY_STOP_LIMIT = 6
        mocked.ORDER_TYPE_SELL_STOP_LIMIT = 7
        mocked.ORDER_TYPE_CLOSE_BY = 12
        
        mocked.POSITION_TYPE_BUY = 0
        mocked.POSITION_TYPE_SELL = 1
        
        mocked.ORDER_TIME_GTC = 0
        mocked.ORDER_TIME_DAY = 1
        mocked.ORDER_TIME_SPECIFIED = 2
        mocked.ORDER_TIME_SPECIFIED_DAY = 3
        
        yield mocked

class TestTrade:
    def test_init(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        assert t._api == api
        with patch('apps.mt5.trade.get_mt5_api') as mock_get_api:
            mock_get_api.return_value = api
            t2 = Trade()
            assert t2._api == api

    def test_log_level(self, mock_mt5):
        t = Trade(api=MagicMock())
        assert t.LogLevel() == 0
        assert t.LogLevel(1) == 1
        assert t.LogLevel() == 1

    def test_set_parameters(self, mock_mt5):
        t = Trade(api=MagicMock())
        t.SetExpertMagicNumber(123)
        assert t._magic == 123
        t.SetDeviationInPoints(10)
        assert t._deviation == 10
        t.SetTypeFilling(1)
        assert t._type_filling == 1
        t.SetAsyncMode(True)
        assert t._async is True

    def test_set_type_filling_by_symbol(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        info = MagicMock()
        info._asdict.return_value = {"trade_fill_mode": mock_mt5.ORDER_FILLING_IOC}
        api.symbol_info.return_value = info
        assert t.SetTypeFillingBySymbol("EURUSD") is True
        assert t._type_filling == mock_mt5.ORDER_FILLING_IOC
        api.symbol_info.return_value = None
        assert t.SetTypeFillingBySymbol("UNKNOWN") is False

    def test_set_margin_mode(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        api.account_info.return_value = {"margin_mode": 1}
        assert t.SetMarginMode() is True
        assert t._margin_mode == 1
        # Test dict fallback
        api.account_info.return_value = {"margin_mode": 2}
        assert t.SetMarginMode() is True
        assert t._margin_mode == 2
        # Test failure
        api.account_info.return_value = None
        assert t.SetMarginMode() is False

    def test_internal_tick(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        api.symbol_info_tick.return_value = {"bid": 1.1}
        assert t._tick("EURUSD") == {"bid": 1.1}
        api.symbol_info_tick.return_value = None
        assert t._tick("EURUSD") is None

    def test_is_success_branches(self, mock_mt5):
        t = Trade(api=MagicMock())
        # attr retcode
        assert t._is_success(MagicMock(retcode=mock_mt5.TRADE_RETCODE_DONE)) is True
        # dict retcode
        assert t._is_success({"retcode": mock_mt5.TRADE_RETCODE_PLACED}) is True
        # none
        assert t._is_success(None) is False
        # other type
        assert t._is_success(123) is False
        # fail retcode
        assert t._is_success({"retcode": 999}) is False

    def test_normalize_result(self, mock_mt5):
        t = Trade(api=MagicMock())
        assert t._normalize_result(None) == {}
        # asdict
        res = MagicMock()
        res._asdict.return_value = {"a": 1}
        assert t._normalize_result(res) == {"a": 1}
        # dict
        assert t._normalize_result({"b": 2}) == {"b": 2}
        # other
        assert t._normalize_result(123) == {"result": 123}

    def test_perform_check(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        # Success asdict
        check = MagicMock()
        check._asdict.return_value = {"balance": 1000}
        api.order_check.return_value = check
        assert t._perform_check({}) == {"balance": 1000}
        # Success dict
        api.order_check.return_value = {"balance": 2000}
        assert t._perform_check({}) == {"balance": 2000}
        # Failure None
        api.order_check.return_value = None
        assert t._perform_check({}) == {}
        # No attribute
        del t._api.order_check
        assert t._perform_check({}) == {}

    def test_resolve_filling_mode_branches(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        # trade_fill_mode
        api.symbol_info.return_value = {"trade_fill_mode": mock_mt5.ORDER_FILLING_FOK}
        assert t._resolve_filling_mode("SYM") == mock_mt5.ORDER_FILLING_FOK
        # filling_mode masks
        api.symbol_info.return_value = {"filling_mode": mock_mt5.ORDER_FILLING_IOC}
        assert t._resolve_filling_mode("SYM") == mock_mt5.ORDER_FILLING_IOC
        api.symbol_info.return_value = {"filling_mode": mock_mt5.ORDER_FILLING_RETURN}
        assert t._resolve_filling_mode("SYM") == mock_mt5.ORDER_FILLING_RETURN
        api.symbol_info.return_value = {"filling_mode": mock_mt5.ORDER_FILLING_FOK}
        assert t._resolve_filling_mode("SYM") == mock_mt5.ORDER_FILLING_FOK
        # default fail
        api.symbol_info.return_value = {"filling_mode": 0}
        assert t._resolve_filling_mode("SYM") is None
        # None
        api.symbol_info.return_value = None
        assert t._resolve_filling_mode("SYM") is None

    def test_send_request_and_retries(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        # 10030 retry
        api.order_send.side_effect = [{"retcode": 10030}, {"retcode": mock_mt5.TRADE_RETCODE_DONE}]
        assert t._send_request({"type_filling": 1}) is True
        # comment retry
        api.order_send.side_effect = [{"retcode": 999, "comment": "Unsupported filling mode"}, {"retcode": mock_mt5.TRADE_RETCODE_DONE}]
        assert t._send_request({}) is True
        # stop retry
        api.order_send.side_effect = [{"retcode": 999, "comment": "Error"}]
        assert t._send_request({}) is False

    def test_send_request_retry_loop_and_final_fallback(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)

        # Continue within retry loop (first fallback fails, second succeeds).
        api.order_send.side_effect = [
            {"retcode": 10030},
            {"retcode": 999, "comment": "Error"},
            {"retcode": mock_mt5.TRADE_RETCODE_DONE},
        ]
        assert t._send_request({"type_filling": mock_mt5.ORDER_FILLING_FOK}) is True

        # Exhaust all retries, then try final request without type_filling.
        api.order_send.side_effect = [
            {"retcode": 10030},
            {"retcode": 999, "comment": "Error"},
            {"retcode": 999, "comment": "Error"},
            {"retcode": 999, "comment": "Error"},
            {"retcode": 999, "comment": "Error"},
        ]
        assert t._send_request({"type_filling": mock_mt5.ORDER_FILLING_FOK}) is False

    def test_request_base_branches(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        # no symbol_select
        del api.symbol_select
        t._request_base("SYM")
        # symbol_select
        api.symbol_select = MagicMock()
        t._request_base("SYM")
        # type_filling resolution
        t._type_filling = None
        api.symbol_info.return_value = {"trade_fill_mode": 1}
        t._request_base("SYM")
        assert t._type_filling == 1
        # filling and time exist
        t._type_filling = 1
        t._type_time = 2
        req = t._request_base("SYM")
        assert req["type_filling"] == 1
        assert req["type_time"] == 2
        # filling and time ARE NONE
        t._type_filling = None
        t._type_time = None
        api.symbol_info.return_value = None
        req = t._request_base("SYM")
        assert "type_filling" not in req
        assert "type_time" not in req

    def test_order_operations_branches(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        api.order_send.return_value = {"retcode": mock_mt5.TRADE_RETCODE_DONE}
        # OrderOpen no stoplimit, no time, no expiration
        assert t.OrderOpen("SYM", 0, 0.1, 1.1) is True
        # OrderOpen with all
        dt = datetime(2025, 1, 1)
        assert t.OrderOpen("SYM", 0, 0.1, 1.1, stoplimit=1.0, type_time=1, expiration=dt) is True
        # OrderModify branches
        assert t.OrderModify(123, 1.1, stoplimit=1.0, type_time=1, expiration=dt) is True
        assert t.OrderModify(123, 1.1) is True
        # OrderDelete
        assert t.OrderDelete(123) is True

    def test_position_operations_branches(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        api.order_send.return_value = {"retcode": mock_mt5.TRADE_RETCODE_DONE}
        
        # PositionOpen SELL and price 0.0
        api.symbol_info_tick.return_value = {"ask": 1.1, "bid": 1.0}
        assert t.PositionOpen("SYM", mock_mt5.ORDER_TYPE_SELL, 0.1, price=0.0) is True
        # tick failures
        api.symbol_info_tick.return_value = None
        assert t.PositionOpen("SYM", 0, 0.1) is False
        api.symbol_info_tick.return_value = 123
        assert t.PositionOpen("SYM", 0, 0.1) is False
        
        # PositionModify failures
        api.positions_get.return_value = None
        assert t.PositionModify("SYM") is False
        api.positions_get.return_value = [123]
        assert t.PositionModify("SYM") is False
        # PositionModify success asdict
        pos = MagicMock()
        pos._asdict.return_value = {"id": 123, "symbol": "SYM", "type": 0}
        api.positions_get.return_value = [pos]
        assert t.PositionModify(ticket=123) is True
        
        # PositionClose branches
        api.symbol_info_tick.return_value = {"ask": 1.1, "bid": 1.0}
        # BUY pos -> closes by SELL
        api.positions_get.return_value = [{"ticket": 123, "symbol": "SYM", "type": mock_mt5.POSITION_TYPE_BUY, "volume": 0.1}]
        assert t.PositionClose("SYM") is True
        # SELL pos -> closes by BUY
        api.positions_get.return_value = [{"ticket": 123, "symbol": "SYM", "type": mock_mt5.POSITION_TYPE_SELL, "volume": 0.1}]
        assert t.PositionClose("SYM") is True
        # pos lookup fail
        api.positions_get.return_value = None
        assert t.PositionClose("SYM") is False
        # pos unknown type fail
        api.positions_get.return_value = [123]
        assert t.PositionClose("SYM") is False
        # tick lookup fail
        api.positions_get.return_value = [{"symbol": "SYM"}]
        api.symbol_info_tick.return_value = None
        assert t.PositionClose("SYM") is False
        # tick unknown type fail
        api.symbol_info_tick.return_value = 123
        assert t.PositionClose("SYM") is False
        
        # PositionClosePartial branches
        api.symbol_info_tick.return_value = {"ask": 1.1, "bid": 1.0}
        api.positions_get.return_value = [{"ticket": 123, "symbol": "SYM", "type": 0, "volume": 0.5}]
        assert t.PositionClosePartial("SYM", 0.1) is True
        # pos lookup fail
        api.positions_get.return_value = None
        assert t.PositionClosePartial("SYM", 0.1) is False
        # pos unknown type fail
        api.positions_get.return_value = [123]
        assert t.PositionClosePartial("SYM", 0.1) is False
        # tick lookup fail
        api.positions_get.return_value = [{"symbol": "SYM"}]
        api.symbol_info_tick.return_value = None
        assert t.PositionClosePartial("SYM", 0.1) is False
        # tick unknown type fail
        api.symbol_info_tick.return_value = 123
        assert t.PositionClosePartial("SYM", 0.1) is False
        
        # PositionCloseBy
        assert t.PositionCloseBy(123, 456) is True

    def test_position_operations_asdict_and_explicit_price_branches(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        api.order_send.return_value = {"retcode": mock_mt5.TRADE_RETCODE_DONE}

        # PositionOpen tick _asdict branch + explicit price branch (price != 0.0).
        tick = MagicMock()
        tick._asdict.return_value = {"ask": 1.2, "bid": 1.1}
        api.symbol_info_tick.return_value = tick
        assert t.PositionOpen("SYM", mock_mt5.ORDER_TYPE_BUY, 0.1, price=1.2345) is True

        # PositionModify dict branch.
        api.positions_get.return_value = [{"ticket": 123, "symbol": "SYM"}]
        assert t.PositionModify(ticket=123, sl=1.0, tp=2.0) is True

        # PositionClose position _asdict + tick _asdict branches.
        pos = MagicMock()
        pos._asdict.return_value = {
            "ticket": 123,
            "symbol": "SYM",
            "type": mock_mt5.POSITION_TYPE_BUY,
            "volume": 0.1,
        }
        tick2 = MagicMock()
        tick2._asdict.return_value = {"ask": 1.2, "bid": 1.1}
        api.positions_get.return_value = [pos]
        api.symbol_info_tick.return_value = tick2
        assert t.PositionClose(ticket=123) is True

        # PositionClosePartial position _asdict + tick _asdict + SELL branch.
        pos_sell = MagicMock()
        pos_sell._asdict.return_value = {
            "ticket": 456,
            "symbol": "SYM",
            "type": mock_mt5.POSITION_TYPE_SELL,
            "volume": 0.3,
        }
        tick3 = MagicMock()
        tick3._asdict.return_value = {"ask": 1.25, "bid": 1.15}
        api.positions_get.return_value = [pos_sell]
        api.symbol_info_tick.return_value = tick3
        assert t.PositionClosePartial(ticket=456, volume=0.1) is True

    def test_aliases(self, mock_mt5):
        t = Trade(api=MagicMock())
        t._api.order_send.return_value = {"retcode": mock_mt5.TRADE_RETCODE_DONE}
        t._api.symbol_info_tick.return_value = {"ask": 1.1, "bid": 1.0}
        assert t.Buy(0.1, "SYM") is True
        assert t.Sell(0.1, "SYM") is True
        assert t.BuyLimit(0.1, "SYM", 1.0) is True
        assert t.BuyStop(0.1, "SYM", 1.2) is True
        assert t.SellLimit(0.1, "SYM", 1.2) is True
        assert t.SellStop(0.1, "SYM", 1.0) is True

    def test_request_accessors(self, mock_mt5):
        t = Trade(api=MagicMock())
        req = {
            "action": mock_mt5.TRADE_ACTION_DEAL,
            "magic": 123,
            "order": 456,
            "symbol": "SYM",
            "volume": 0.1,
            "price": 1.1,
            "stoplimit": 1.05,
            "sl": 1.0,
            "tp": 1.2,
            "deviation": 5,
            "type": mock_mt5.ORDER_TYPE_BUY,
            "type_filling": mock_mt5.ORDER_FILLING_FOK,
            "type_time": mock_mt5.ORDER_TIME_GTC,
            "expiration": 9999,
            "comment": "test",
            "position": 777,
            "position_by": 888
        }
        t._last_request = req
        assert t.Request() == req
        assert t.RequestAction() == req["action"]
        assert t.RequestMagic() == 123
        assert t.RequestOrder() == 456
        assert t.RequestSymbol() == "SYM"
        assert t.RequestVolume() == 0.1
        assert t.RequestPrice() == 1.1
        assert t.RequestStopLimit() == 1.05
        assert t.RequestSL() == 1.0
        assert t.RequestTP() == 1.2
        assert t.RequestDeviation() == 5
        assert t.RequestType() == req["type"]
        assert t.RequestTypeFilling() == req["type_filling"]
        assert t.RequestTypeTime() == req["type_time"]
        assert t.RequestExpiration() == 9999
        assert t.RequestComment() == "test"
        assert t.RequestPosition() == 777
        assert t.RequestPositionBy() == 888
        
        # fallback magic
        t._last_request.pop("magic")
        assert t.RequestMagic() == t._magic
        
        # Descriptions
        maps = [
            ("RequestActionDescription", "action", mock_mt5.TRADE_ACTION_PENDING, "Pending"),
            ("RequestActionDescription", "action", mock_mt5.TRADE_ACTION_SLTP, "SL/TP"),
            ("RequestActionDescription", "action", mock_mt5.TRADE_ACTION_MODIFY, "Modify"),
            ("RequestActionDescription", "action", mock_mt5.TRADE_ACTION_REMOVE, "Remove"),
            ("RequestActionDescription", "action", 999, "Unknown"),
            ("RequestTypeDescription", "type", mock_mt5.ORDER_TYPE_SELL, "Sell"),
            ("RequestTypeDescription", "type", mock_mt5.ORDER_TYPE_BUY_LIMIT, "Buy Limit"),
            ("RequestTypeDescription", "type", mock_mt5.ORDER_TYPE_SELL_LIMIT, "Sell Limit"),
            ("RequestTypeDescription", "type", mock_mt5.ORDER_TYPE_BUY_STOP, "Buy Stop"),
            ("RequestTypeDescription", "type", mock_mt5.ORDER_TYPE_SELL_STOP, "Sell Stop"),
            ("RequestTypeDescription", "type", mock_mt5.ORDER_TYPE_BUY_STOP_LIMIT, "Buy Stop Limit"),
            ("RequestTypeDescription", "type", mock_mt5.ORDER_TYPE_SELL_STOP_LIMIT, "Sell Stop Limit"),
            ("RequestTypeDescription", "type", mock_mt5.ORDER_TYPE_CLOSE_BY, "Close By"),
            ("RequestTypeDescription", "type", 999, "Unknown"),
            ("RequestTypeFillingDescription", "type_filling", mock_mt5.ORDER_FILLING_IOC, "IOC"),
            ("RequestTypeFillingDescription", "type_filling", mock_mt5.ORDER_FILLING_RETURN, "Return"),
            ("RequestTypeFillingDescription", "type_filling", 999, "Unknown"),
            ("RequestTypeTimeDescription", "type_time", mock_mt5.ORDER_TIME_DAY, "Day"),
            ("RequestTypeTimeDescription", "type_time", mock_mt5.ORDER_TIME_SPECIFIED, "Specified"),
            ("RequestTypeTimeDescription", "type_time", mock_mt5.ORDER_TIME_SPECIFIED_DAY, "Specified Day"),
            ("RequestTypeTimeDescription", "type_time", 999, "Unknown"),
        ]
        for meth, key, val, expected in maps:
            t._last_request[key] = val
            assert getattr(t, meth)() == expected

    def test_result_accessors(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        res = {"retcode": 10009, "deal": 1, "order": 2, "volume": 0.1, "price": 1.1, "bid": 1.0, "ask": 1.2, "comment": "ok"}
        t._last_result = res
        assert t.Result() == res
        assert t.ResultRetcode() == 10009
        assert t.ResultDeal() == 1
        assert t.ResultOrder() == 2
        assert t.ResultVolume() == 0.1
        assert t.ResultPrice() == 1.1
        assert t.ResultBid() == 1.0
        assert t.ResultAsk() == 1.2
        assert t.ResultComment() == "ok"
        # descriptions
        del api.trade_retcode_description
        assert t.ResultRetcodeDescription() == "10009"
        api.trade_retcode_description = MagicMock(return_value="Done")
        assert t.ResultRetcodeDescription() == "Done"

    def test_check_result_accessors(self, mock_mt5):
        api = MagicMock()
        t = Trade(api=api)
        res = {"retcode": 10009, "balance": 100.0, "equity": 110.0, "profit": 10.0, "margin": 1.0, "margin_free": 109.0, "margin_level": 11000.0, "comment": "ok"}
        t._last_check = res
        assert t.CheckResult() == res
        assert t.CheckResultRetcode() == 10009
        assert t.CheckResultBalance() == 100.0
        assert t.CheckResultEquity() == 110.0
        assert t.CheckResultProfit() == 10.0
        assert t.CheckResultMargin() == 1.0
        assert t.CheckResultMarginFree() == 109.0
        assert t.CheckResultMarginLevel() == 11000.0
        assert t.CheckResultComment() == "ok"
        # descriptions
        del api.trade_retcode_description
        assert t.CheckResultRetcodeDescription() == "10009"
        api.trade_retcode_description = MagicMock(return_value="Done")
        assert t.CheckResultRetcodeDescription() == "Done"

    def test_printing(self, mock_mt5):
        t = Trade(api=MagicMock())
        t._last_request = {"a": 1}
        t._last_result = {"b": 2}
        assert "Request" in t.FormatRequest()
        assert "Result" in t.FormatRequestResult()
        with patch('builtins.print') as mock_print:
            t.PrintRequest()
            t.PrintResult()
            assert mock_print.call_count == 2

    def test_get_position_branches(self, mock_mt5):
        t = Trade(api=MagicMock())
        # ticket
        t._api.positions_get.return_value = [{"ticket": 1}]
        assert t._get_position(ticket=1) == {"ticket": 1}
        # symbol
        t._api.positions_get.return_value = [{"symbol": "SYM"}]
        assert t._get_position(symbol="SYM") == {"symbol": "SYM"}
        # none
        assert t._get_position() is None
        # empty
        t._api.positions_get.return_value = []
        assert t._get_position(symbol="SYM") is None
