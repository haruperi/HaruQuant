/**
 * @file test_broker_adapter_interface.cpp
 * @brief Tests for BrokerAdapter abstraction, MockBroker, and PaperTradingEngine.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <memory>

namespace {

using hqt::sim::MockBroker;
using hqt::sim::PaperTradingEngine;
using hqt::sim::SimulatorClient;
using hqt::sim::SymbolInfoData;
using hqt::sim::SymbolTickData;
using hqt::sim::TradeRequest;

SimulatorClient make_client() {
    SimulatorClient client;

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

TEST(BrokerAdapterTest, MockBrokerConnectSubmitFetchState) {
    MockBroker broker(make_client());
    ASSERT_TRUE(broker.connect());

    TradeRequest req;
    req.action = 1;
    req.type = 0;
    req.symbol = "EURUSD";
    req.volume = 1.0;

    const auto result = broker.submit(req);
    ASSERT_EQ(result.retcode, 10009);
    ASSERT_GT(result.order, 0U);

    const auto snapshot = broker.fetch_state();
    ASSERT_TRUE(snapshot.positions.count("EURUSD") > 0);
    EXPECT_DOUBLE_EQ(snapshot.positions.at("EURUSD").net_volume, 1.0);
}

TEST(BrokerAdapterTest, MockBrokerDeterministicPartialFill) {
    MockBroker broker(make_client());
    ASSERT_TRUE(broker.connect());
    broker.set_partial_fill_ratio(0.5);
    broker.set_deterministic_price(1.20000);

    TradeRequest req;
    req.action = 1;
    req.type = 0;
    req.symbol = "EURUSD";
    req.volume = 1.0;

    const auto result = broker.submit(req);
    ASSERT_EQ(result.retcode, 10010);

    const auto snapshot = broker.fetch_state();
    ASSERT_TRUE(snapshot.positions.count("EURUSD") > 0);
    EXPECT_DOUBLE_EQ(snapshot.positions.at("EURUSD").net_volume, 0.5);
}

TEST(BrokerAdapterTest, PaperTradingEngineRoutesThroughAdapter) {
    auto broker = std::make_shared<MockBroker>(make_client());
    PaperTradingEngine engine(std::static_pointer_cast<hqt::sim::BrokerAdapter>(broker));
    ASSERT_TRUE(engine.connect());

    TradeRequest req;
    req.action = 5;
    req.type = 2;  // BUY_LIMIT
    req.symbol = "EURUSD";
    req.volume = 0.2;
    req.price = 1.09500;

    const auto placed = engine.submit_order(req);
    ASSERT_EQ(placed.retcode, 10008);
    ASSERT_GT(placed.order, 0U);

    const auto canceled = engine.cancel_order(placed.order);
    EXPECT_EQ(canceled.retcode, 10009);
}

}  // namespace
