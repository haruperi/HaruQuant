/**
FILE: tests\test_currency_margin.cpp

PURPOSE:
Defines test_currency_margin.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_currency_margin.cpp.
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
#include "util/currency_converter.hpp"
#include "util/margin_calculator.hpp"
#include "trading/market_state.hpp"
#include <gtest/gtest.h>

using namespace hqt;

// =============================================================================
// CurrencyConverter Tests
// =============================================================================

class CurrencyConverterTest : public ::testing::Test {
protected:
    CurrencyConverter converter;
};

TEST_F(CurrencyConverterTest, DirectConversion) {
    converter.register_pair("EUR", "USD", 1.10);

    double result = converter.convert(100.0, "EUR", "USD");
    EXPECT_DOUBLE_EQ(result, 110.0);
}

TEST_F(CurrencyConverterTest, InvertedConversion) {
    converter.register_pair("EUR", "USD", 1.10);

    // Convert USD -> EUR using inverted rate
    double result = converter.convert(110.0, "USD", "EUR");
    EXPECT_NEAR(result, 100.0, 0.01);
}

TEST_F(CurrencyConverterTest, SameCurrencyConversion) {
    double result = converter.convert(100.0, "USD", "USD");
    EXPECT_DOUBLE_EQ(result, 100.0);
}

TEST_F(CurrencyConverterTest, MultiHopConversion) {
    // EUR -> USD -> JPY
    converter.register_pair("EUR", "USD", 1.10);
    converter.register_pair("USD", "JPY", 150.0);

    double result = converter.convert(100.0, "EUR", "JPY");
    EXPECT_NEAR(result, 16500.0, 0.1);  // 100 * 1.10 * 150
}

TEST_F(CurrencyConverterTest, MultiHopWithInverse) {
    // EUR -> USD -> GBP (using GBP/USD inverse)
    converter.register_pair("EUR", "USD", 1.10);
    converter.register_pair("GBP", "USD", 1.25);  // GBP/USD

    // EUR -> USD -> GBP
    double result = converter.convert(100.0, "EUR", "GBP");
    EXPECT_NEAR(result, 88.0, 0.1);  // 100 * 1.10 / 1.25
}

TEST_F(CurrencyConverterTest, NoPathThrowsError) {
    converter.register_pair("EUR", "USD", 1.10);

    // Try to convert to unregistered currency
    EXPECT_THROW(
        converter.convert(100.0, "EUR", "JPY"),
        ConversionPathError
    );
}

TEST_F(CurrencyConverterTest, UpdateRate) {
    converter.register_pair("EUR", "USD", 1.10);
    EXPECT_DOUBLE_EQ(converter.get_rate("EUR", "USD"), 1.10);

    converter.update_rate("EUR", "USD", 1.12, 1000);
    EXPECT_DOUBLE_EQ(converter.get_rate("EUR", "USD"), 1.12);

    double result = converter.convert(100.0, "EUR", "USD");
    EXPECT_DOUBLE_EQ(result, 112.0);
}

TEST_F(CurrencyConverterTest, HasPair) {
    EXPECT_FALSE(converter.has_pair("EUR", "USD"));

    converter.register_pair("EUR", "USD", 1.10);

    EXPECT_TRUE(converter.has_pair("EUR", "USD"));
    EXPECT_FALSE(converter.has_pair("USD", "EUR"));  // Not registered directly
    EXPECT_FALSE(converter.has_pair("EUR", "JPY"));
}

TEST_F(CurrencyConverterTest, GetRateThrowsForMissingPair) {
    EXPECT_THROW(
        converter.get_rate("EUR", "USD"),
        ConversionPathError
    );
}

TEST_F(CurrencyConverterTest, FindPathDirect) {
    converter.register_pair("EUR", "USD", 1.10);

    auto path = converter.find_path("EUR", "USD");
    ASSERT_EQ(path.size(), 2);
    EXPECT_EQ(path[0], "EUR");
    EXPECT_EQ(path[1], "USD");
}

TEST_F(CurrencyConverterTest, FindPathMultiHop) {
    converter.register_pair("EUR", "USD", 1.10);
    converter.register_pair("USD", "JPY", 150.0);

    auto path = converter.find_path("EUR", "JPY");
    ASSERT_EQ(path.size(), 3);
    EXPECT_EQ(path[0], "EUR");
    EXPECT_EQ(path[1], "USD");
    EXPECT_EQ(path[2], "JPY");
}

TEST_F(CurrencyConverterTest, FindPathNoPath) {
    converter.register_pair("EUR", "USD", 1.10);

    auto path = converter.find_path("EUR", "JPY");
    EXPECT_TRUE(path.empty());
}

TEST_F(CurrencyConverterTest, FindPathSameCurrency) {
    auto path = converter.find_path("USD", "USD");
    ASSERT_EQ(path.size(), 1);
    EXPECT_EQ(path[0], "USD");
}

TEST_F(CurrencyConverterTest, ValidatePaths) {
    converter.register_pair("EUR", "USD", 1.10);
    converter.register_pair("USD", "JPY", 150.0);
    converter.register_pair("GBP", "USD", 1.25);

    // All currencies connected through USD
    EXPECT_NO_THROW(converter.validate_paths());
}

TEST_F(CurrencyConverterTest, ValidatePathsDisconnected) {
    converter.register_pair("EUR", "USD", 1.10);
    converter.register_pair("GBP", "AUD", 1.80);  // Disconnected component

    // Graph has two disconnected components
    EXPECT_THROW(converter.validate_paths(), ConversionPathError);
}

TEST_F(CurrencyConverterTest, PairCount) {
    EXPECT_EQ(converter.pair_count(), 0);

    converter.register_pair("EUR", "USD", 1.10);
    EXPECT_EQ(converter.pair_count(), 1);

    converter.register_pair("USD", "JPY", 150.0);
    EXPECT_EQ(converter.pair_count(), 2);
}

TEST_F(CurrencyConverterTest, Clear) {
    converter.register_pair("EUR", "USD", 1.10);
    converter.register_pair("USD", "JPY", 150.0);
    EXPECT_EQ(converter.pair_count(), 2);

    converter.clear();
    EXPECT_EQ(converter.pair_count(), 0);
    EXPECT_FALSE(converter.has_pair("EUR", "USD"));
}

// =============================================================================
// MarginCalculator Tests
// =============================================================================

class MarginCalculatorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Setup currency converter
        converter.register_pair("EUR", "USD", 1.10);
        converter.register_pair("USD", "JPY", 150.0);
        converter.register_pair("GBP", "USD", 1.25);

        calc = std::make_unique<MarginCalculator>(converter);

        // Setup EURUSD symbol
        eurusd.Name("EURUSD");
        eurusd.SetDigits(5);
        eurusd.SetPoint(0.00001);
        eurusd.SetContractSize(100000.0);
        eurusd.SetVolumeMin(0.01);
        eurusd.SetVolumeMax(100.0);
        eurusd.SetVolumeStep(0.01);
        eurusd.SetCurrencyBase("EUR");
        eurusd.SetCurrencyProfit("USD");

        // Setup account
        account.AddBalance(static_cast<int64_t>(10000.0 * 1000000));  // Fixed-point
        account.SetLeverage(100);
        // Currency is not settable in MT5 API - it's part of account identity
    }

    CurrencyConverter converter;
    std::unique_ptr<MarginCalculator> calc;
    SymbolInfo eurusd;
    AccountInfo account;
};

TEST_F(MarginCalculatorTest, RequiredMargin) {
    // 1 lot EUR/USD at 1.10000 with 1:100 leverage
    // Margin = (1.0 * 100000 * 1.10) / 100 = 1100
    double margin = calc->required_margin(
        eurusd,
        ENUM_POSITION_TYPE::POSITION_TYPE_BUY,
        1.0,
        1.10000,
        100
    );

    EXPECT_DOUBLE_EQ(margin, 1100.0);
}

TEST_F(MarginCalculatorTest, RequiredMarginMiniLot) {
    // 0.1 lot (mini lot)
    double margin = calc->required_margin(
        eurusd,
        ENUM_POSITION_TYPE::POSITION_TYPE_BUY,
        0.1,
        1.10000,
        100
    );

    EXPECT_DOUBLE_EQ(margin, 110.0);
}

TEST_F(MarginCalculatorTest, RequiredMarginHighLeverage) {
    // 1:500 leverage
    double margin = calc->required_margin(
        eurusd,
        ENUM_POSITION_TYPE::POSITION_TYPE_BUY,
        1.0,
        1.10000,
        500
    );

    EXPECT_DOUBLE_EQ(margin, 220.0);  // 110000 / 500
}

TEST_F(MarginCalculatorTest, MarginLevel) {
    double equity = 10000.0;
    double margin = 1000.0;

    double level = calc->margin_level(equity, margin);
    EXPECT_DOUBLE_EQ(level, 1000.0);  // (10000 / 1000) * 100 = 1000%
}

TEST_F(MarginCalculatorTest, MarginLevelLowEquity) {
    double equity = 500.0;
    double margin = 1000.0;

    double level = calc->margin_level(equity, margin);
    EXPECT_DOUBLE_EQ(level, 50.0);  // (500 / 1000) * 100 = 50%
}

TEST_F(MarginCalculatorTest, MarginLevelZeroMargin) {
    double equity = 10000.0;
    double margin = 0.0;

    double level = calc->margin_level(equity, margin);
    EXPECT_TRUE(std::isinf(level));
}

TEST_F(MarginCalculatorTest, FreeMargin) {
    double equity = 10000.0;
    double margin = 1000.0;

    double free = calc->free_margin(equity, margin);
    EXPECT_DOUBLE_EQ(free, 9000.0);
}

TEST_F(MarginCalculatorTest, HasSufficientMargin) {
    std::vector<PositionInfo> positions;
    std::unordered_map<std::string, SymbolInfo> symbols;
    symbols["EURUSD"] = eurusd;

    // Account has 10000 balance, no unrealized P&L, so equity = 10000
    // Need 1100 margin for 1 lot, have 10000 equity
    bool sufficient = calc->has_sufficient_margin(
        account,
        positions,
        symbols,
        1100.0,
        100.0  // Min margin level 100%
    );

    EXPECT_TRUE(sufficient);
}

TEST_F(MarginCalculatorTest, InsufficientMargin) {
    std::vector<PositionInfo> positions;
    std::unordered_map<std::string, SymbolInfo> symbols;

    // Create new account with low balance (1000)
    // Pass 0.0 as initial balance to avoid default 10000
    AccountInfo low_balance_account(0.0, "USD", 100);
    low_balance_account.AddBalance(static_cast<int64_t>(1000.0 * 1000000));

    // Need 1100 margin but only have 1000 equity
    // Margin level would be (1000 / 1100) * 100 = 90.9%
    // This is below the 100% minimum, so should be insufficient
    bool sufficient = calc->has_sufficient_margin(
        low_balance_account,
        positions,
        symbols,
        1100.0,
        100.0
    );

    // Actually with new margin of 1100 and equity of 1000:
    // Margin level = (1000 / 1100) * 100 = 90.9% which is < 100%
    EXPECT_FALSE(sufficient);
}

TEST_F(MarginCalculatorTest, ShouldStopOutFalse) {
    std::vector<PositionInfo> positions;
    std::unordered_map<std::string, SymbolInfo> symbols;

    // High equity (10000), no stop-out
    bool stop_out = calc->should_stop_out(account, positions, symbols, 20.0);
    EXPECT_FALSE(stop_out);
}

TEST_F(MarginCalculatorTest, FindLargestLoser) {
    std::vector<PositionInfo> positions;

    PositionInfo pos1, pos2, pos3;
    pos1.SetProfitFP(static_cast<int64_t>(100.0 * 1000000));
    pos2.SetProfitFP(static_cast<int64_t>(-500.0 * 1000000));  // Largest loser
    pos3.SetProfitFP(static_cast<int64_t>(-200.0 * 1000000));

    positions.push_back(pos1);
    positions.push_back(pos2);
    positions.push_back(pos3);

    int loser_idx = calc->find_largest_loser(positions);
    EXPECT_EQ(loser_idx, 1);  // Index of pos2
}

TEST_F(MarginCalculatorTest, FindLargestLoserAllProfitable) {
    std::vector<PositionInfo> positions;

    PositionInfo pos1, pos2;
    pos1.SetProfitFP(static_cast<int64_t>(100.0 * 1000000));
    pos2.SetProfitFP(static_cast<int64_t>(200.0 * 1000000));

    positions.push_back(pos1);
    positions.push_back(pos2);

    int loser_idx = calc->find_largest_loser(positions);
    EXPECT_EQ(loser_idx, -1);  // No losers
}

TEST_F(MarginCalculatorTest, IsMarginCall) {
    double equity = 900.0;
    double margin = 1000.0;

    // Margin level = 90%, below margin call level of 100%
    bool margin_call = calc->is_margin_call(equity, margin, 100.0);
    EXPECT_TRUE(margin_call);
}

TEST_F(MarginCalculatorTest, MaxVolume) {
    double available_margin = 5000.0;
    int leverage = 100;
    double price = 1.10000;

    // max_volume = (5000 * 100) / (100000 * 1.10) = 4.545 lots
    // Rounded down to step (0.01) = 4.54 lots
    double max_vol = calc->max_volume(
        eurusd,
        ENUM_POSITION_TYPE::POSITION_TYPE_BUY,
        price,
        available_margin,
        leverage
    );

    EXPECT_NEAR(max_vol, 4.54, 0.01);
}

TEST_F(MarginCalculatorTest, HedgingMode) {
    EXPECT_TRUE(calc->is_hedging_mode());  // Default is hedging

    calc->set_hedging_mode(false);
    EXPECT_FALSE(calc->is_hedging_mode());

    calc->set_hedging_mode(true);
    EXPECT_TRUE(calc->is_hedging_mode());
}

// =============================================================================
// MarketState Tests
// =============================================================================

TEST(MarketStateTest, UpdatePrice) {
    MarketState market;

    market.update_price("EURUSD", 1.10000, 1.10005);

    EXPECT_TRUE(market.has_symbol("EURUSD"));
    EXPECT_DOUBLE_EQ(market.get_bid("EURUSD"), 1.10000);
    EXPECT_DOUBLE_EQ(market.get_ask("EURUSD"), 1.10005);
}

TEST(MarketStateTest, GetSpread) {
    MarketState market;

    market.update_price("EURUSD", 1.10000, 1.10005);

    double spread = market.get_spread("EURUSD");
    EXPECT_NEAR(spread, 0.00005, 0.0000001);  // Floating point tolerance
}

TEST(MarketStateTest, GetMid) {
    MarketState market;

    market.update_price("EURUSD", 1.10000, 1.10010);

    double mid = market.get_mid("EURUSD");
    EXPECT_DOUBLE_EQ(mid, 1.10005);
}

TEST(MarketStateTest, HasSymbolFalse) {
    MarketState market;

    EXPECT_FALSE(market.has_symbol("EURUSD"));

    market.update_price("EURUSD", 1.10000, 1.10005);

    EXPECT_TRUE(market.has_symbol("EURUSD"));
    EXPECT_FALSE(market.has_symbol("GBPUSD"));
}

TEST(MarketStateTest, RemoveSymbol) {
    MarketState market;

    market.update_price("EURUSD", 1.10000, 1.10005);
    EXPECT_TRUE(market.has_symbol("EURUSD"));

    market.remove_symbol("EURUSD");
    EXPECT_FALSE(market.has_symbol("EURUSD"));
}

TEST(MarketStateTest, Clear) {
    MarketState market;

    market.update_price("EURUSD", 1.10000, 1.10005);
    market.update_price("GBPUSD", 1.25000, 1.25005);
    EXPECT_EQ(market.size(), 2);

    market.clear();
    EXPECT_EQ(market.size(), 0);
}

TEST(MarketStateTest, IsStale) {
    MarketState market;

    int64_t now = 1000000;
    market.update_price("EURUSD", 1.10000, 1.10005, now);

    // Not stale immediately
    EXPECT_FALSE(market.is_stale("EURUSD", now, 60'000'000));

    // Stale after max age
    EXPECT_TRUE(market.is_stale("EURUSD", now + 61'000'000, 60'000'000));
}

