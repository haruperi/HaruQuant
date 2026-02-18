"""Tests for the hqt_engine.sim C++ simulation bindings."""

import sys
from pathlib import Path

import pytest

# Add build output to path so hqt_engine can be imported
_build_dir = Path(__file__).resolve().parents[2] / "build" / "bridge" / "Release"
if _build_dir.exists():
    sys.path.insert(0, str(_build_dir))

try:
    import hqt_engine
    from hqt_engine import sim

    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ engine not built")


# ── DTO defaults ──────────────────────────────────────────────────────


class TestDTODefaults:
    def test_simulator_state_defaults(self):
        s = sim.SimulatorState()
        assert s.running is False
        assert s.paused is False
        assert s.current_time_us == 0
        assert s.current_bar_index == 0
        assert s.processed_events == 0

    def test_account_info_data_defaults(self):
        a = sim.AccountInfoData()
        assert a.login == 12345678
        assert a.leverage == 100
        assert a.balance == 10000.0
        assert a.trade_allowed is True
        assert a.currency == "USD"

    def test_symbol_tick_data_defaults(self):
        t = sim.SymbolTickData()
        assert t.time == 0
        assert t.bid == 0.0
        assert t.ask == 0.0

    def test_symbol_info_data_defaults(self):
        si = sim.SymbolInfoData()
        assert si.symbol == "EURUSD"
        assert si.digits == 5
        assert si.point == pytest.approx(0.00001)
        assert si.trade_contract_size == 100000.0

    def test_trade_record_data_defaults(self):
        r = sim.TradeRecordData()
        assert r.ticket == 0
        assert r.volume == 0.0
        assert r.symbol == ""

    def test_trade_request_defaults(self):
        r = sim.TradeRequest()
        assert r.action == 0
        assert r.volume == 0.0
        assert r.symbol == ""

    def test_trade_result_defaults(self):
        r = sim.TradeResult()
        assert r.retcode == 10011
        assert r.deal == 0

    def test_backtest_bar_step_defaults(self):
        b = sim.BacktestBarStep()
        assert b.time_msc == 0
        assert b.close == 0.0
        assert b.entry_signal == 0
        assert b.exit_signal == 0

    def test_position_totals_defaults(self):
        pt = sim.PositionTotals()
        assert pt.profit == 0.0
        assert pt.margin == 0.0

    def test_tick_model_bar_defaults(self):
        b = sim.TickModelBar()
        assert b.time_msc == 0
        assert b.open == 0.0
        assert b.spread_points == -1.0

    def test_model_tick_defaults(self):
        t = sim.ModelTick()
        assert t.time_msc == 0
        assert t.bid == 0.0

    def test_trade_record_defaults(self):
        r = sim.TradeRecord()
        assert r.ticket == 0
        assert r.is_buy is True
        assert r.profit_loss == 0.0

    def test_portfolio_symbol_input_defaults(self):
        p = sim.PortfolioSymbolInput()
        assert p.symbol == ""
        assert p.bars == []

    def test_result_metrics_summary_defaults(self):
        s = sim.ResultMetricsSummary()
        assert s.initial_balance == 0.0
        assert s.total_trades == 0
        assert s.win_rate == 0.0


# ── DTO mutation ──────────────────────────────────────────────────────


class TestDTOMutation:
    def test_simulator_state_mutation(self):
        s = sim.SimulatorState()
        s.running = True
        s.processed_events = 42
        assert s.running is True
        assert s.processed_events == 42

    def test_account_info_data_mutation(self):
        a = sim.AccountInfoData()
        a.balance = 50000.0
        a.leverage = 200
        assert a.balance == 50000.0
        assert a.leverage == 200

    def test_backtest_bar_step_mutation(self):
        b = sim.BacktestBarStep()
        b.close = 1.2345
        b.entry_signal = 1
        b.sl = 1.2300
        b.tp = 1.2400
        assert b.close == 1.2345
        assert b.entry_signal == 1


# ── to_dict ───────────────────────────────────────────────────────────


class TestToDict:
    def test_account_info_to_dict(self):
        a = sim.AccountInfoData()
        d = a.to_dict()
        assert isinstance(d, dict)
        assert "balance" in d
        assert isinstance(d["balance"], str)

    def test_symbol_info_to_dict(self):
        si = sim.SymbolInfoData()
        d = si.to_dict()
        assert isinstance(d, dict)
        assert "symbol" in d

    def test_symbol_tick_to_dict(self):
        t = sim.SymbolTickData()
        d = t.to_dict()
        assert isinstance(d, dict)
        assert "bid" in d

    def test_trade_record_data_to_dict(self):
        r = sim.TradeRecordData()
        d = r.to_dict()
        assert isinstance(d, dict)
        assert "ticket" in d


# ── TradeSimulator basics ────────────────────────────────────────────


class TestTradeSimulator:
    def test_default_construction(self):
        client = sim.TradeSimulator()
        acct = client.account_info()
        assert acct.balance == 10000.0

    def test_custom_account(self):
        acct = sim.AccountInfoData()
        acct.balance = 50000.0
        client = sim.TradeSimulator(acct)
        assert client.account_info().balance == 50000.0

    def test_symbol_info_roundtrip(self):
        client = sim.TradeSimulator()
        si = sim.SymbolInfoData()
        si.symbol = "GBPUSD"
        si.digits = 5
        client.set_symbol_info(si)
        result = client.symbol_info("GBPUSD")
        assert result is not None
        assert result.symbol == "GBPUSD"
        assert result.digits == 5

    def test_symbol_info_unknown_returns_none(self):
        client = sim.TradeSimulator()
        assert client.symbol_info("UNKNOWN") is None

    def test_symbol_info_tick_unknown_returns_none(self):
        client = sim.TradeSimulator()
        assert client.symbol_info_tick("UNKNOWN") is None

    def test_last_error(self):
        client = sim.TradeSimulator()
        code, msg = client.last_error()
        assert code == 1
        assert msg == "Success"


# ── Calc functions ────────────────────────────────────────────────────


class TestCalcFunctions:
    def test_order_calc_margin(self):
        client = sim.TradeSimulator()
        si = sim.SymbolInfoData()
        si.symbol = "EURUSD"
        client.set_symbol_info(si)
        margin = client.order_calc_margin(0, "EURUSD", 1.0, 1.10000)
        assert margin > 0.0

    def test_order_calc_profit(self):
        client = sim.TradeSimulator()
        si = sim.SymbolInfoData()
        si.symbol = "EURUSD"
        client.set_symbol_info(si)
        profit = client.order_calc_profit(0, "EURUSD", 1.0, 1.10000, 1.10100)
        assert profit != 0.0

    def test_free_calc_margin(self):
        # calc_margin(trade_calc_mode, volume, price, contract_size,
        #             leverage, tick_size, tick_value, margin_initial)
        margin = sim.calc_margin(0, 1.0, 1.10000, 100000.0, 100.0, 0.00001, 1.0, 0.0)
        assert margin > 0.0

    def test_free_calc_profit(self):
        # calc_profit(action, volume, price_open, price_close,
        #             tick_size, tick_value, contract_size)
        profit = sim.calc_profit(0, 1.0, 1.10000, 1.10100, 0.00001, 1.0, 100000.0)
        assert profit == pytest.approx(100.0, abs=1.0)


# ── BacktestEngine smoke ─────────────────────────────────────────────


def _make_client_with_symbol(symbol="EURUSD"):
    """Helper: create client with registered symbol + initial tick."""
    client = sim.TradeSimulator()
    si = sim.SymbolInfoData()
    si.symbol = symbol
    client.set_symbol_info(si)
    tick = sim.SymbolTickData()
    tick.bid = 1.10000
    tick.ask = 1.10010
    client.set_symbol_tick(symbol, tick)
    return client


class TestBacktestEngine:
    def test_smoke(self):
        client = _make_client_with_symbol()
        engine = sim.BacktestEngine(client)

        bars = []
        for i in range(5):
            b = sim.BacktestBarStep()
            b.time_msc = (i + 1) * 60000
            b.close = 1.10000 + i * 0.00010
            b.entry_signal = 1 if i == 0 else 0  # buy on first bar
            b.exit_signal = -1 if i == 4 else 0   # not used, close buys=1
            bars.append(b)
        # Set exit_signal=1 on last bar (close buys)
        bars[4].exit_signal = 1

        engine.run_trading_timeframe("EURUSD", 0.01, bars)
        assert engine.state().processed_events == 5

    def test_completed_trades(self):
        client = _make_client_with_symbol()
        engine = sim.BacktestEngine(client)

        bars = []
        for i in range(3):
            b = sim.BacktestBarStep()
            b.time_msc = (i + 1) * 60000
            b.close = 1.10000 + i * 0.00010
            b.entry_signal = 1 if i == 0 else 0
            b.exit_signal = 1 if i == 2 else 0
            bars.append(b)

        engine.run_trading_timeframe("EURUSD", 0.01, bars)
        trades = engine.completed_trades()
        assert isinstance(trades, list)


# ── Callback ──────────────────────────────────────────────────────────


class TestCallback:
    def test_on_bar_processed(self):
        client = _make_client_with_symbol()
        engine = sim.BacktestEngine(client)

        calls = []

        def on_bar(index, bar, state):
            calls.append((index, bar.close, state.processed_events))

        engine.set_on_bar_processed(on_bar)

        bars = []
        for i in range(3):
            b = sim.BacktestBarStep()
            b.time_msc = (i + 1) * 60000
            b.close = 1.10000 + i * 0.00010
            bars.append(b)

        engine.run_trading_timeframe("EURUSD", 0.01, bars)
        assert len(calls) == 3
        assert calls[0][0] == 0  # first index
        assert calls[2][0] == 2  # last index


# ── TickModel ─────────────────────────────────────────────────────────


class TestTickModel:
    def test_generate_m1_ohlc(self):
        bar = sim.TickModelBar()
        bar.time_msc = 1000
        bar.open = 1.10000
        bar.high = 1.10050
        bar.low = 1.09950
        bar.close = 1.10020
        bar.spread_points = 10.0

        ticks = sim.TickModel.generate_m1_ohlc([bar], 0.00001, 10.0)
        assert isinstance(ticks, list)
        assert len(ticks) > 0
        assert isinstance(ticks[0], sim.ModelTick)

    def test_generate_synthetic_ticks(self):
        bar = sim.TickModelBar()
        bar.time_msc = 1000
        bar.open = 1.10000
        bar.high = 1.10050
        bar.low = 1.09950
        bar.close = 1.10020

        ticks = sim.TickModel.generate_synthetic_ticks([bar], 0.00001, 10.0)
        assert len(ticks) > 0

    def test_model_tick_equality(self):
        a = sim.ModelTick()
        a.time_msc = 100
        a.bid = 1.1
        a.ask = 1.2
        a.last = 1.15

        b = sim.ModelTick()
        b.time_msc = 100
        b.bid = 1.1
        b.ask = 1.2
        b.last = 1.15

        assert a == b


# ── PortfolioEngine ───────────────────────────────────────────────────


class TestPortfolioEngine:
    def test_run_equal_weight(self):
        client = sim.TradeSimulator()

        for sym in ["EURUSD", "GBPUSD"]:
            si = sim.SymbolInfoData()
            si.symbol = sym
            client.set_symbol_info(si)
            tick = sim.SymbolTickData()
            tick.bid = 1.10000
            tick.ask = 1.10010
            client.set_symbol_tick(sym, tick)

        inputs = []
        for sym in ["EURUSD", "GBPUSD"]:
            inp = sim.PortfolioSymbolInput()
            inp.symbol = sym
            bars = []
            for i in range(3):
                b = sim.BacktestBarStep()
                b.time_msc = (i + 1) * 60000
                b.close = 1.10000 + i * 0.00010
                bars.append(b)
            inp.bars = bars
            inputs.append(inp)

        engine = sim.PortfolioEngine(client)
        engine.run_equal_weight(inputs, 0.01)
        allocs = engine.effective_allocations()
        assert isinstance(allocs, dict)
        assert len(allocs) == 2


# ── ResultMetrics ─────────────────────────────────────────────────────


class TestResultMetrics:
    def test_from_trades(self):
        trades = []
        for i in range(3):
            t = sim.TradeRecord()
            t.ticket = i + 1
            t.profit_loss = 100.0 if i < 2 else -50.0
            trades.append(t)

        summary = sim.ResultMetrics.from_trades(trades, 10000.0, 10150.0)
        assert summary.total_trades == 3
        assert summary.winning_trades == 2
        assert summary.losing_trades == 1
        assert summary.initial_balance == 10000.0
        assert summary.final_balance == 10150.0


# ── AutoCloseReason enum ─────────────────────────────────────────────


class TestAutoCloseReason:
    def test_values(self):
        assert sim.AutoCloseReason.StopLoss.value == 1
        assert sim.AutoCloseReason.TakeProfit.value == 2

    def test_enum_identity(self):
        assert sim.AutoCloseReason.StopLoss != sim.AutoCloseReason.TakeProfit


