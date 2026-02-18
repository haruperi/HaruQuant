/**
 * @file test_twap_vwap.cpp
 * @brief Tests for TWAP/VWAP scheduling and execution quality metrics.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <cmath>
#include <memory>

namespace {

using hqt::sim::ExecutionAlgoTWAP;
using hqt::sim::ExecutionAlgoVWAP;
using hqt::sim::ExecutionPolicy;
using hqt::sim::ExecutionRouter;
using hqt::sim::MockBroker;
using hqt::sim::TradeSimulator;
using hqt::sim::SymbolInfoData;
using hqt::sim::SymbolTickData;
using hqt::sim::TradeRequest;

TradeSimulator make_client() {
    TradeSimulator client;

    SymbolInfoData symbol;
    symbol.symbol = "EURUSD";
    symbol.digits = 5;
    symbol.point = 0.00001;
    symbol.spread = 10;
    symbol.volume_min = 0.01;
    symbol.volume_step = 0.01;
    symbol.volume_max = 100.0;
    symbol.trade_contract_size = 100000.0;
    symbol.trade_tick_size = 0.00001;
    symbol.trade_tick_value = 1.0;
    symbol.bid = 1.10000;
    symbol.ask = 1.10010;
    client.set_symbol_info(symbol);

    SymbolTickData tick;
    tick.bid = 1.10000;
    tick.ask = 1.10010;
    tick.last = 1.10000;
    tick.time = 1700000000;
    tick.time_msc = 1700000000000;
    client.set_symbol_tick("EURUSD", tick);

    return client;
}

TradeRequest market_buy(double volume = 1.0) {
    TradeRequest req;
    req.action = 1;
    req.type = 0;
    req.symbol = "EURUSD";
    req.volume = volume;
    return req;
}

TEST(ExecutionAlgoTest, TwapBuildsEqualSlices) {
    const auto slices = ExecutionAlgoTWAP::build_schedule(1.0, 0, 3000, 4);
    ASSERT_EQ(slices.size(), 4U);
    EXPECT_NEAR(slices[0].volume, 0.25, 1e-9);
    EXPECT_NEAR(slices[1].volume, 0.25, 1e-9);
    EXPECT_NEAR(slices[2].volume, 0.25, 1e-9);
    EXPECT_NEAR(slices[3].volume, 0.25, 1e-9);
    EXPECT_EQ(slices[0].scheduled_time_ms, 0);
    EXPECT_EQ(slices[3].scheduled_time_ms, 3000);
}

TEST(ExecutionAlgoTest, VwapBuildsVolumeWeightedSlices) {
    const auto slices = ExecutionAlgoVWAP::build_schedule(1.0, 0, 3000, {1.0, 2.0, 3.0, 4.0});
    ASSERT_EQ(slices.size(), 4U);
    EXPECT_NEAR(slices[0].volume, 0.1, 1e-9);
    EXPECT_NEAR(slices[1].volume, 0.2, 1e-9);
    EXPECT_NEAR(slices[2].volume, 0.3, 1e-9);
    EXPECT_NEAR(slices[3].volume, 0.4, 1e-9);
}

TEST(ExecutionAlgoTest, RouterTracksPartialFillAndLatencyMetrics) {
    auto broker = std::make_shared<MockBroker>(make_client());
    broker->set_partial_fill_ratio(0.5);

    ExecutionPolicy policy;
    policy.max_orders_per_window = 10;
    ExecutionRouter router(broker, policy);
    ASSERT_TRUE(router.connect());
    router.set_risk_account_state(10000.0, 10000.0, 0.0, 0.0);

    const auto routed = router.submit(market_buy(1.0));
    EXPECT_EQ(routed.result.retcode, 10010);

    const auto summary = router.quality_summary();
    EXPECT_EQ(summary.samples, 1U);
    EXPECT_EQ(summary.partial_fill_count, 1U);
    EXPECT_NEAR(summary.partial_fill_rate, 1.0, 1e-9);
    EXPECT_GE(summary.p99_latency_ms, 0.0);
}

}  // namespace


