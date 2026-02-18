/**
 * @file test_portfolio_state.cpp
 * @brief Tests for thread-safe portfolio state aggregation.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

#include <thread>
#include <vector>

namespace {

using hqt::sim::PortfolioState;

TEST(PortfolioStateTest, TracksCapitalMarginAndPnl) {
    PortfolioState state(10000.0, "USD");

    state.upsert_position("strat_a", "EURUSD", 0.50, 400.0, 25.0);
    state.upsert_position("strat_b", "EURUSD", -0.20, 150.0, -5.0);
    state.upsert_position("strat_b", "GBPUSD", 1.00, 700.0, 15.0);

    auto account = state.account_snapshot();
    EXPECT_NEAR(account.balance, 10000.0, 1e-9);
    EXPECT_NEAR(account.margin, 1250.0, 1e-9);
    EXPECT_NEAR(account.profit, 35.0, 1e-9);
    EXPECT_NEAR(account.equity, 10035.0, 1e-9);

    state.apply_realized_pnl("strat_a", "EURUSD", 50.0, 2.0, 0.0);
    account = state.account_snapshot();
    EXPECT_NEAR(state.total_realized_pnl(), 48.0, 1e-9);
    EXPECT_NEAR(account.balance, 10048.0, 1e-9);
    EXPECT_NEAR(account.equity, 10083.0, 1e-9);

    const auto by_symbol = state.positions_by_symbol();
    ASSERT_TRUE(by_symbol.count("EURUSD") > 0U);
    EXPECT_NEAR(by_symbol.at("EURUSD").net_volume, 0.30, 1e-9);
    EXPECT_NEAR(by_symbol.at("EURUSD").margin, 550.0, 1e-9);
}

TEST(PortfolioStateTest, SupportsConcurrentMultiStrategyUpdates) {
    PortfolioState state(10000.0, "USD");
    std::vector<std::thread> workers;
    workers.reserve(8);

    for (int i = 0; i < 8; ++i) {
        workers.emplace_back([&state, i]() {
            const std::string strategy = "strat_" + std::to_string(i % 3);
            const std::string symbol = "SYM_" + std::to_string(i);
            state.upsert_position(strategy, symbol, 1.0 + static_cast<double>(i), 100.0 + i, 10.0 + i);
            state.apply_realized_pnl(strategy, symbol, 5.0 + i, 0.0, 0.0);
        });
    }

    for (auto& worker : workers) {
        worker.join();
    }

    const auto account = state.account_snapshot();
    EXPECT_NEAR(account.margin, 828.0, 1e-9);
    EXPECT_NEAR(account.profit, 108.0, 1e-9);
    EXPECT_NEAR(state.total_realized_pnl(), 68.0, 1e-9);
    EXPECT_NEAR(account.balance, 10068.0, 1e-9);
    EXPECT_NEAR(account.equity, 10176.0, 1e-9);
}

}  // namespace

