/**
FILE: tests\test_engine_trading.cpp

PURPOSE:
Defines test_engine_trading.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_engine_trading.cpp.
- File-local helpers supporting the main public or internal entry points.

DATA FLOW:
Callers provide requests or data -> this file applies core logic -> outputs state changes or results.

DEPENDENCIES:
- Internal modules: Neighboring headers under cpp/include and shared utility components.
- External systems: Standard C++ library and optional third-party libs linked by CMake.

DESIGN NOTES:
- Keep behavior deterministic for backtest and unit-test reliability.
- Prefer explicit validation and retcode-based failure signaling.
- Preserve low coupling between domains through typed interfaces.
*/
#include <gtest/gtest.h>

#include "engine/engine.hpp"
#include "util/error.hpp"

#include <cmath>
#include <memory>
#include <string>
#include <vector>

namespace {

using hqt::AccountInfo;
using hqt::ENUM_SYMBOL_CALC_MODE;
using hqt::ENUM_ORDER_TYPE;
using hqt::SymbolInfo;
using hqt::util::error_from_retcode;
using hqt::util::is_success_retcode;
using hqt::sim::ExecutionAlgoTWAP;
using hqt::sim::ExecutionAlgoVWAP;
using hqt::sim::ExecutionPolicy;
using hqt::sim::ExecutionRouter;
using hqt::sim::MockBroker;
using hqt::sim::PaperTradingEngine;
using hqt::sim::SymbolTickData;
using hqt::sim::TradeRecordTracker;
using hqt::sim::TradeRequest;
using hqt::sim::TradeSimulator;

SymbolInfo make_symbol() {
    SymbolInfo symbol;
    symbol.SetSymbolId(1);
    symbol.Name("EURUSD");
    symbol.SetDigits(5);
    symbol.SetPoint(0.00001);
    symbol.SetTickSize(0.00001);
    symbol.SetTickValue(1.0);
    symbol.SetContractSize(100000.0);
    symbol.SetVolumeMin(0.01);
    symbol.SetVolumeMax(100.0);
    symbol.SetVolumeStep(0.01);
    symbol.SetVolumeLimit(100.0);
    symbol.SetMarginInitial(100.0);
    symbol.SetSpread(20);
    symbol.SetStopsLevel(10);
    symbol.SetFreezeLevel(0);
    symbol.SetTradeCalcMode(ENUM_SYMBOL_CALC_MODE::SYMBOL_CALC_MODE_FOREX);
    symbol.UpdatePrice(1.10000, 1.10020, 0);
    return symbol;
}

TradeSimulator make_simulator() {
    AccountInfo account(10000.0, "USD", 100);
    account.SetBalance(10000.0);
    account.SetEquity(10000.0);
    account.SetFreeMargin(10000.0);
    TradeSimulator sim(account);
    sim.set_symbol_info(make_symbol());
    SymbolTickData tick;
    tick.time = 1;
    tick.time_msc = 1000;
    tick.bid = 1.10000;
    tick.ask = 1.10020;
    tick.last = 1.10010;
    sim.set_symbol_tick("EURUSD", tick);
    return sim;
}

TEST(EngineTradingTest, CalcMarginAndProfitCoverModesAndFallback) {
    const double volume = 1.0;
    const double price = 1.10;
    const double contract_size = 100000.0;
    const double leverage = 100.0;
    const double tick_size = 0.00001;
    const double tick_value = 1.0;
    const double margin_initial = 1000.0;

    EXPECT_GT(hqt::sim::calc_margin(0, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial), 0.0);
    EXPECT_GT(hqt::sim::calc_margin(4, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial), 0.0);
    EXPECT_GT(hqt::sim::calc_margin(7, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial), 0.0);
    EXPECT_GT(hqt::sim::calc_margin(99, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial), 0.0);

    const double buy_profit = hqt::sim::calc_profit(0, 0, 1.0, 1.10000, 1.10100, tick_size, tick_value, contract_size);
    const double sell_profit = hqt::sim::calc_profit(0, 1, 1.0, 1.10100, 1.10000, tick_size, tick_value, contract_size);
    EXPECT_GT(buy_profit, 0.0);
    EXPECT_GT(sell_profit, 0.0);
    EXPECT_DOUBLE_EQ(hqt::sim::calc_profit(0, 0, 1.0, 1.10000, 1.10100, 0.0, 0.0, 0.0), 0.0);
}

TEST(EngineTradingTest, TradeRecordTrackerLifecycle) {
    TradeRecordTracker tracker;
    tracker.on_open(1001, "EURUSD", true, 0.1, 1.1000, 1.0900, 1.1200, 1000, 50.0);
    tracker.on_open(1001, "EURUSD", true, 0.1, 1.1000, 1.0900, 1.1200, 1000, 50.0);
    EXPECT_TRUE(tracker.has_open(1001));

    tracker.on_update(1001, 15.0);
    tracker.on_update(1001, -10.0);
    EXPECT_TRUE(tracker.on_close(1001, 5000, 1.1010, 20.0));
    EXPECT_FALSE(tracker.has_open(1001));

    const auto& completed = tracker.completed_trades();
    ASSERT_EQ(completed.size(), 1U);
    EXPECT_EQ(completed.front().ticket, 1001U);
    EXPECT_GT(completed.front().time_in_trade_seconds, 0.0);
    EXPECT_NEAR(completed.front().r_multiple, 0.4, 1e-12);
}

TEST(EngineTradingTest, TradeSimulatorMarketLifecycleAndIdempotency) {
    TradeSimulator sim = make_simulator();

    EXPECT_TRUE(sim.symbol_select("EURUSD", true));
    EXPECT_GE(sim.symbols_total(), 1U);
    EXPECT_EQ(sim.order_state_name(0), "UNKNOWN");

    const auto open_result = sim.PositionOpen(
        "EURUSD",
        static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY),
        0.10,
        1.10020,
        1.09900,
        1.10150,
        "open");
    EXPECT_TRUE(is_success_retcode(open_result.retcode));
    EXPECT_GT(sim.positions_total(), 0U);

    const auto positions = sim.positions_get();
    ASSERT_FALSE(positions.empty());
    const uint64_t position_ticket = positions.front().Ticket();

    const auto modify_result = sim.PositionModify(std::nullopt, position_ticket, 1.09850, 1.10200);
    EXPECT_TRUE(is_success_retcode(modify_result.retcode));

    const auto close_result = sim.PositionClose(std::nullopt, position_ticket, 10);
    EXPECT_TRUE(is_success_retcode(close_result.retcode));

    EXPECT_GT(sim.order_calc_margin(0, "EURUSD", 0.1, 1.10020), 0.0);
    EXPECT_EQ(sim.order_calc_margin(0, "UNKNOWN", 0.1, 1.10020), 0.0);
    EXPECT_NE(sim.order_calc_profit(0, "EURUSD", 0.1, 1.10000, 1.10100), 0.0);
    EXPECT_EQ(sim.order_calc_profit(0, "UNKNOWN", 0.1, 1.10000, 1.10100), 0.0);

    TradeRequest req;
    req.action = 1;
    req.type = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    req.symbol = "EURUSD";
    req.volume = 0.10;
    req.price = 1.10020;
    req.client_order_id = "cid-1";

    const auto first = sim.order_send(req);
    const auto second = sim.order_send(req);
    EXPECT_EQ(first.retcode, second.retcode);
    EXPECT_EQ(first.order, second.order);

    req.price = 1.10030;
    const auto duplicate_payload = sim.order_send(req);
    EXPECT_EQ(duplicate_payload.retcode, 10013);
}

TEST(EngineTradingTest, TradeSimulatorPendingOrderLifecycleAndOrderState) {
    TradeSimulator sim = make_simulator();

    const auto open_pending = sim.OrderOpen(
        "EURUSD",
        static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT),
        0.10,
        1.09900,
        0.0,
        1.09800,
        1.10200,
        0,
        0,
        "pending");
    EXPECT_TRUE(is_success_retcode(open_pending.retcode));
    EXPECT_GT(sim.orders_total(), 0U);

    const auto orders = sim.orders_get();
    ASSERT_FALSE(orders.empty());
    const uint64_t order_ticket = orders.front().Ticket();

    const auto modify = sim.OrderModify(order_ticket, 1.09850, 1.09750, 1.10150, 0.0, 0, "mod");
    EXPECT_TRUE(is_success_retcode(modify.retcode));
    EXPECT_NE(sim.order_state_name(order_ticket), "UNKNOWN");

    const auto remove = sim.OrderDelete(order_ticket, "delete");
    EXPECT_TRUE(is_success_retcode(remove.retcode));
}

TEST(EngineTradingTest, MockBrokerPaperAndExecutionRouterPaths) {
    TradeSimulator sim = make_simulator();
    MockBroker broker(sim);

    TradeRequest request;
    request.action = 1;
    request.type = static_cast<int>(ENUM_ORDER_TYPE::ORDER_TYPE_BUY);
    request.symbol = "EURUSD";
    request.volume = 0.20;
    request.price = 1.10020;

    const auto disconnected_submit = broker.submit(request);
    EXPECT_EQ(disconnected_submit.retcode, 10031);

    broker.set_partial_fill_ratio(0.5);
    broker.set_deterministic_price(1.10020);
    EXPECT_TRUE(broker.connect());
    const auto partial = broker.submit(request);
    EXPECT_TRUE(is_success_retcode(partial.retcode));
    EXPECT_GT(partial.volume, 0.0);
    EXPECT_LE(partial.volume, request.volume);
    broker.clear_deterministic_price();

    PaperTradingEngine no_adapter(nullptr);
    EXPECT_FALSE(no_adapter.connect());
    EXPECT_EQ(no_adapter.submit_order(request).retcode, 10031);
    EXPECT_EQ(no_adapter.cancel_order(1).retcode, 10031);

    auto adapter = std::make_shared<MockBroker>(make_simulator());
    PaperTradingEngine paper(adapter);
    EXPECT_TRUE(paper.connect());
    EXPECT_TRUE(is_success_retcode(paper.submit_order(request).retcode));
    const auto snapshot = paper.snapshot_state();
    EXPECT_GE(snapshot.account.Balance(), 0.0);

    ExecutionPolicy policy;
    policy.max_retries = 1;
    policy.max_orders_per_window = 1;
    policy.rate_limit_window_ms = 60000;
    ExecutionRouter router(adapter, policy);
    ASSERT_TRUE(router.connect());
    router.set_risk_account_state(10000.0, 10000.0, 0.0, 0.0);

    const auto route1 = router.submit(request, 0.1, 0.1, 10.0, 10000.0, true);
    EXPECT_TRUE(is_success_retcode(route1.result.retcode));

    const auto route2 = router.submit(request, 0.1, 0.1, 10.0, 10000.0, true);
    EXPECT_TRUE(route2.rate_limited);
    EXPECT_EQ(route2.result.retcode, 10024);

    ExecutionRouter risk_router(adapter, policy);
    ASSERT_TRUE(risk_router.connect());
    risk_router.set_risk_account_state(7000.0, 10000.0, 0.0, 0.0);
    const auto blocked = risk_router.submit(request, 0.1, 0.1, 10.0, 10000.0, true);
    EXPECT_TRUE(blocked.risk_blocked);
    EXPECT_EQ(blocked.policy_code, "MAX_DRAWDOWN");

    const auto quality = router.quality_summary();
    EXPECT_GT(quality.samples, 0U);
}

TEST(EngineTradingTest, ExecutionAlgoSchedules) {
    EXPECT_TRUE(ExecutionAlgoTWAP::build_schedule(0.0, 0, 1000, 4).empty());
    const auto twap = ExecutionAlgoTWAP::build_schedule(1.0, 1000, 4000, 4);
    ASSERT_EQ(twap.size(), 4U);
    double twap_sum = 0.0;
    for (const auto& slice : twap) {
        twap_sum += slice.volume;
    }
    EXPECT_NEAR(twap_sum, 1.0, 1e-12);

    const auto vwap_fallback = ExecutionAlgoVWAP::build_schedule(1.0, 1000, 4000, {0.0, 0.0, 0.0});
    ASSERT_EQ(vwap_fallback.size(), 3U);

    const auto vwap = ExecutionAlgoVWAP::build_schedule(1.0, 1000, 4000, {1.0, 2.0, 1.0});
    ASSERT_EQ(vwap.size(), 3U);
    EXPECT_GT(vwap[1].volume, vwap[0].volume);
}

TEST(EngineTradingTest, EngineFacadeDelegatesToBacktestEngine) {
    TradeSimulator sim = make_simulator();
    hqt::engine::Engine engine(sim);

    std::vector<hqt::sim::BacktestBarStep> bars{
        {1000, 1.10010, 20.0, 0, 0, 0.0, 0.0},
    };
    engine.run_trading_timeframe("EURUSD", 0.10, bars);
    EXPECT_EQ(engine.state().processed_events, 1U);
    EXPECT_TRUE(engine.completed_trades().empty());

    std::vector<hqt::sim::ModelTick> ticks{
        {1000, 1.10000, 1.10020, 1.10010},
    };
    engine.run_trading_timeframe_with_ticks("EURUSD", 0.10, bars, ticks);
    EXPECT_EQ(engine.state().processed_events, 1U);
}

TEST(EngineTradingTest, ErrorMappingCoversKnownAndFallbackCodes) {
    const auto known = error_from_retcode(10021);
    EXPECT_EQ(known.code, 10021);
    EXPECT_EQ(known.domain, "trade");
    EXPECT_TRUE(known.retryable);

    const auto mt5_runtime = error_from_retcode(4301);
    EXPECT_EQ(mt5_runtime.domain, "mt5");
    EXPECT_EQ(mt5_runtime.name, "MT5_RUNTIME_ERROR");

    const auto user_error = error_from_retcode(65537);
    EXPECT_EQ(user_error.name, "USER_ERROR");

    EXPECT_TRUE(is_success_retcode(10009));
    EXPECT_FALSE(is_success_retcode(10011));
}

}  // namespace

