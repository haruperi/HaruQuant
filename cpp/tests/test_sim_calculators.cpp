/**
 * @file test_sim_calculators.cpp
 * @brief Tests for simulator margin/profit calculators.
 */

#include <gtest/gtest.h>
#include "engine/engine.hpp"

namespace {

using hqt::sim::TradeSimulator;
using hqt::sim::SymbolInfoData;

constexpr double kEps = 1e-9;

TEST(SimCalculatorsTest, MarginModesCovered) {
    const double volume = 1.5;
    const double price = 1.2;
    const double contract_size = 100000.0;
    const double leverage = 100.0;
    const double tick_size = 0.0001;
    const double tick_value = 10.0;
    const double margin_initial = 500.0;

    EXPECT_NEAR(hqt::sim::calc_margin(0, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial),
                (volume * contract_size) / leverage, kEps);
    EXPECT_NEAR(hqt::sim::calc_margin(1, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial),
                volume * contract_size, kEps);
    EXPECT_NEAR(hqt::sim::calc_margin(2, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial),
                volume * contract_size * price, kEps);
    EXPECT_NEAR(hqt::sim::calc_margin(3, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial),
                (volume * contract_size * price) / leverage, kEps);
    EXPECT_NEAR(hqt::sim::calc_margin(4, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial),
                volume * contract_size * price * tick_value / tick_size, kEps);
    EXPECT_NEAR(hqt::sim::calc_margin(5, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial),
                volume * contract_size * price, kEps);
    EXPECT_NEAR(hqt::sim::calc_margin(6, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial),
                volume * contract_size * price, kEps);
    EXPECT_NEAR(hqt::sim::calc_margin(7, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial),
                volume * margin_initial, kEps);
    EXPECT_NEAR(hqt::sim::calc_margin(8, volume, price, contract_size, leverage, tick_size, tick_value, margin_initial),
                volume * margin_initial, kEps);
}

TEST(SimCalculatorsTest, ProfitBuySellSymmetry) {
    const double volume = 2.0;
    const double open = 1.1000;
    const double close = 1.1020;
    const double tick_size = 0.0001;
    const double tick_value = 10.0;
    const double contract_size = 100000.0;

    const double buy_profit =
        hqt::sim::calc_profit(0, volume, open, close, tick_size, tick_value, contract_size);
    const double sell_profit =
        hqt::sim::calc_profit(1, volume, open, close, tick_size, tick_value, contract_size);

    EXPECT_GT(buy_profit, 0.0);
    EXPECT_LT(sell_profit, 0.0);
    EXPECT_NEAR(buy_profit, -sell_profit, kEps);
}

TEST(SimCalculatorsTest, ProfitFallsBackToContractSizeWhenTickValueUnavailable) {
    const double volume = 1.0;
    const double open = 1.1000;
    const double close = 1.1015;
    const double contract_size = 100000.0;

    const double profit = hqt::sim::calc_profit(0, volume, open, close, 0.0, 0.0, contract_size);
    EXPECT_NEAR(profit, (close - open) * contract_size * volume, kEps);
}

TEST(SimCalculatorsTest, TradeSimulatorUsesSymbolCalculatorParams) {
    TradeSimulator client;
    SymbolInfoData info;
    info.symbol = "EURUSD";
    info.trade_calc_mode = 3;
    info.trade_contract_size = 100000.0;
    info.trade_tick_size = 0.0001;
    info.trade_tick_value = 10.0;
    info.point = 0.0001;
    client.set_symbol_info(info);

    const double margin = client.order_calc_margin(0, "EURUSD", 1.0, 1.2);
    EXPECT_NEAR(margin, (1.0 * 100000.0 * 1.2) / 100.0, kEps);

    const double profit = client.order_calc_profit(0, "EURUSD", 1.0, 1.1000, 1.1010);
    EXPECT_NEAR(profit, ((1.1010 - 1.1000) / 0.0001) * 10.0, 1e-6);
}

TEST(SimCalculatorsTest, TradeSimulatorReturnsZeroForUnknownSymbol) {
    TradeSimulator client;

    EXPECT_DOUBLE_EQ(client.order_calc_margin(0, "UNKNOWN", 1.0, 1.2), 0.0);
    EXPECT_DOUBLE_EQ(client.order_calc_profit(0, "UNKNOWN", 1.0, 1.1, 1.2), 0.0);
}

}  // namespace



