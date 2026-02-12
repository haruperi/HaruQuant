/**
 * @file test_sim_portfolio_engine.cpp
 * @brief Tests for multi-symbol portfolio engine execution/allocation.
 */

#include <gtest/gtest.h>
#include "sim/portfolio_engine.hpp"

#include <vector>

namespace {

using hqt::sim::BacktestBarStep;
using hqt::sim::PortfolioEngine;
using hqt::sim::PortfolioSymbolInput;
using hqt::sim::SimulatorClient;
using hqt::sim::SymbolInfoData;

class SimPortfolioEngineTest : public ::testing::Test {
protected:
    void SetUp() override {
        eurusd.symbol = "EURUSD";
        eurusd.digits = 5;
        eurusd.point = 0.00001;
        eurusd.spread = 10;
        eurusd.volume_min = 0.01;
        eurusd.volume_step = 0.01;
        eurusd.volume_max = 100.0;
        eurusd.trade_contract_size = 100000.0;
        eurusd.trade_tick_size = 0.00001;
        eurusd.trade_tick_value = 1.0;
        eurusd.bid = 1.10000;
        eurusd.ask = 1.10010;
        client.set_symbol_info(eurusd);

        gbpusd = eurusd;
        gbpusd.symbol = "GBPUSD";
        gbpusd.bid = 1.25000;
        gbpusd.ask = 1.25010;
        client.set_symbol_info(gbpusd);
    }

    SimulatorClient client;
    SymbolInfoData eurusd;
    SymbolInfoData gbpusd;
};

TEST_F(SimPortfolioEngineTest, MultiSymbolExecutionWithEqualWeight) {
    PortfolioEngine engine(client);

    const std::vector<PortfolioSymbolInput> inputs{
        {
            "EURUSD",
            {
                {1000, 1.10000, 10.0, 1, 0},  // open buy
                {2000, 1.10030, 10.0, 0, 1},  // close buy
            },
        },
        {
            "GBPUSD",
            {
                {1000, 1.25000, 10.0, -1, 0},  // open sell
                {3000, 1.24980, 10.0, 0, -1},  // close sell
            },
        },
    };
    engine.run_equal_weight(inputs, 0.20);

    EXPECT_TRUE(client.positions_get().empty());
    const auto deals = client.history_deals_get();
    EXPECT_EQ(deals.size(), 2U);
}

TEST_F(SimPortfolioEngineTest, AllocationAppliedToVolumeBySymbol) {
    PortfolioEngine engine(client);

    const std::vector<PortfolioSymbolInput> inputs{
        {"EURUSD", {{1000, 1.10000, 10.0, 1, 0}}},
        {"GBPUSD", {{1000, 1.25000, 10.0, -1, 0}}},
    };

    engine.run_with_allocations(inputs, 0.40, {{"EURUSD", 0.25}, {"GBPUSD", 0.75}});

    const auto eur_positions = client.positions_get(std::nullopt, "EURUSD");
    const auto gbp_positions = client.positions_get(std::nullopt, "GBPUSD");
    ASSERT_EQ(eur_positions.size(), 1U);
    ASSERT_EQ(gbp_positions.size(), 1U);

    EXPECT_DOUBLE_EQ(eur_positions[0].volume, 0.10);
    EXPECT_DOUBLE_EQ(gbp_positions[0].volume, 0.30);
}

}  // namespace

