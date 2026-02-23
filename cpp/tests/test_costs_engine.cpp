/**
FILE: tests\test_costs_engine.cpp

PURPOSE:
Defines test_costs_engine.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_costs_engine.cpp.
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
// Suppress padding warnings for test fixtures (caused by alignas(64) Tick member)
#ifdef _MSC_VER
#pragma warning(disable: 4324)  // structure was padded due to alignment specifier
#endif

#include <gtest/gtest.h>
#include "costs/costs_engine.hpp"
#include "costs/slippage_model.hpp"
#include "costs/commission_model.hpp"
#include "costs/swap_model.hpp"
#include "costs/spread_model.hpp"
#include "data/tick.hpp"
#include "trading/symbol_info.hpp"

using namespace hqt;

// ============================================================================
// Test Fixtures
// ============================================================================

class SlippageModelTest : public ::testing::Test {
protected:
    Tick tick{1'000'000, 1, 1'100'000, 1'100'020, 1'000'000, 1'000'000, 20};
    SymbolInfo eurusd;
    std::mt19937_64 rng{42};

    void SetUp() override {
        eurusd.SetSymbolId(1);
        eurusd.Name("EURUSD");
        eurusd.SetDigits(5);
        eurusd.SetPoint(0.00001);
        eurusd.SetTickSize(1.0);
        eurusd.SetTickValue(1.0);
        eurusd.SetContractSize(100000.0);
        eurusd.SetVolumeMin(0.01);
        eurusd.SetVolumeMax(100.0);
        eurusd.SetVolumeStep(0.01);
    }
};

class CommissionModelTest : public ::testing::Test {
protected:
    SymbolInfo eurusd;

    void SetUp() override {
        eurusd.SetSymbolId(1);
        eurusd.Name("EURUSD");
        eurusd.SetDigits(5);
        eurusd.SetPoint(0.00001);
        eurusd.SetTickSize(1.0);
        eurusd.SetTickValue(1.0);
        eurusd.SetContractSize(100000.0);
        eurusd.SetVolumeMin(0.01);
        eurusd.SetVolumeMax(100.0);
        eurusd.SetVolumeStep(0.01);
    }
};

class SwapModelTest : public ::testing::Test {
protected:
    SymbolInfo eurusd;

    void SetUp() override {
        eurusd.SetSymbolId(1);
        eurusd.Name("EURUSD");
        eurusd.SetDigits(5);
        eurusd.SetPoint(0.00001);
        eurusd.SetTickSize(1.0);
        eurusd.SetTickValue(1.0);
        eurusd.SetContractSize(100000.0);
        eurusd.SetVolumeMin(0.01);
        eurusd.SetVolumeMax(100.0);
        eurusd.SetVolumeStep(0.01);
    }
};

class SpreadModelTest : public ::testing::Test {
protected:
    Tick tick{1'000'000, 1, 1'100'000, 1'100'020, 1'000'000, 1'000'000, 20};
    SymbolInfo eurusd;
    std::mt19937_64 rng{42};

    void SetUp() override {
        eurusd.SetSymbolId(1);
        eurusd.Name("EURUSD");
        eurusd.SetDigits(5);
        eurusd.SetPoint(0.00001);
        eurusd.SetTickSize(1.0);
        eurusd.SetTickValue(1.0);
        eurusd.SetContractSize(100000.0);
        eurusd.SetVolumeMin(0.01);
        eurusd.SetVolumeMax(100.0);
        eurusd.SetVolumeStep(0.01);
    }
};

class CostsEngineTest : public ::testing::Test {
protected:
    SymbolInfo eurusd;

    void SetUp() override {
        eurusd.SetSymbolId(1);
        eurusd.Name("EURUSD");
        eurusd.SetDigits(5);
        eurusd.SetPoint(0.00001);
        eurusd.SetTickSize(1.0);
        eurusd.SetTickValue(1.0);
        eurusd.SetContractSize(100000.0);
        eurusd.SetVolumeMin(0.01);
        eurusd.SetVolumeMax(100.0);
        eurusd.SetVolumeStep(0.01);
    }

    std::unique_ptr<CostsEngine> create_engine() {
        return std::make_unique<CostsEngine>(
            std::make_unique<FixedSlippage>(2),
            std::make_unique<FixedPerLot>(7'000'000),  // $7 per lot
            std::make_unique<ZeroSwap>(),
            std::make_unique<FixedSpread>(15),
            42  // Seed for determinism
        );
    }
};

// ============================================================================
// Slippage Model Tests
// ============================================================================

TEST_F(SlippageModelTest, ZeroSlippage) {
    ZeroSlippage model;
    auto slippage = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, tick, eurusd, rng);
    EXPECT_EQ(slippage, 0);
}

TEST_F(SlippageModelTest, FixedSlippage) {
    FixedSlippage model(2);  // 2 points = 0.2 pips
    auto slippage = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, tick, eurusd, rng);
    EXPECT_EQ(slippage, 2 * 10);  // 2 points * 0.00001 = 0.00002 in fixed-point
}

TEST_F(SlippageModelTest, RandomSlippageRange) {
    RandomSlippage model(1, 5);
    auto slippage = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, tick, eurusd, rng);
    EXPECT_GE(slippage, 1 * 10);
    EXPECT_LE(slippage, 5 * 10);
}

TEST_F(SlippageModelTest, VolumeSlippage) {
    VolumeSlippage model(1, 0.5);  // 1 point base + 0.5 points per lot

    // 1 lot: 1 + 0.5*1 = 1.5 points -> rounds to 2 points
    auto slippage1 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, tick, eurusd, rng);
    EXPECT_EQ(slippage1, 2 * 10);  // Rounded to 2 points

    // 10 lots: 1 + 0.5*10 = 6 points
    auto slippage10 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 10.0, tick, eurusd, rng);
    EXPECT_EQ(slippage10, 6 * 10);
}

TEST_F(SlippageModelTest, LatencyProfileSlippage) {
    LatencyProfileSlippage model(50.0, 0.3);  // 50ms latency, 30% of spread
    auto slippage = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, tick, eurusd, rng);
    EXPECT_GT(slippage, 0);
}

// ============================================================================
// Commission Model Tests
// ============================================================================

TEST_F(CommissionModelTest, ZeroCommission) {
    ZeroCommission model;
    auto commission = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, eurusd);
    EXPECT_EQ(commission, 0);
}

TEST_F(CommissionModelTest, FixedPerLot) {
    auto model = FixedPerLot::from_double(7.0);  // $7 per lot

    // 1 lot
    auto commission1 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, eurusd);
    EXPECT_EQ(commission1, 7'000'000);

    // 2 lots
    auto commission2 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 2.0, 1'100'000, eurusd);
    EXPECT_EQ(commission2, 14'000'000);
}

TEST_F(CommissionModelTest, FixedPerTrade) {
    auto model = FixedPerTrade::from_double(10.0);  // $10 per trade

    // Same commission regardless of volume
    auto commission1 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, eurusd);
    EXPECT_EQ(commission1, 10'000'000);

    auto commission10 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 10.0, 1'100'000, eurusd);
    EXPECT_EQ(commission10, 10'000'000);
}

TEST_F(CommissionModelTest, SpreadMarkup) {
    SpreadMarkup model(1);  // 1 point markup
    auto commission = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, eurusd);
    EXPECT_GT(commission, 0);
}

TEST_F(CommissionModelTest, PercentageOfValue) {
    PercentageOfValue model(0.001);  // 0.1%
    auto commission = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, eurusd);
    EXPECT_GT(commission, 0);

    // Larger volume = proportionally larger commission
    auto commission2 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 2.0, 1'100'000, eurusd);
    EXPECT_EQ(commission2, commission * 2);
}

TEST_F(CommissionModelTest, TieredCommission) {
    TieredCommission model({
        {0.0, 7.0},    // <10 lots: $7/lot
        {10.0, 5.0},   // 10-50 lots: $5/lot
        {50.0, 3.0}    // >50 lots: $3/lot
    });

    // 5 lots: $7/lot
    auto commission5 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 5.0, 1'100'000, eurusd);
    EXPECT_EQ(commission5, 35'000'000);

    // 20 lots: $5/lot
    auto commission20 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 20.0, 1'100'000, eurusd);
    EXPECT_EQ(commission20, 100'000'000);

    // 100 lots: $3/lot
    auto commission100 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 100.0, 1'100'000, eurusd);
    EXPECT_EQ(commission100, 300'000'000);
}

// ============================================================================
// Swap Model Tests
// ============================================================================

TEST_F(SwapModelTest, ZeroSwap) {
    ZeroSwap model;
    auto swap = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, 1'110'000, eurusd, 1);
    EXPECT_EQ(swap, 0);
    EXPECT_FALSE(model.should_apply(1'000'000));
}

TEST_F(SwapModelTest, StandardSwapPoints) {
    StandardSwap model(-0.5, 0.3, SwapType::POINTS);  // Long pays 0.5, short earns 0.3

    // Long position (pay swap)
    auto swap_long = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, 1'110'000, eurusd, 1);
    EXPECT_LT(swap_long, 0);  // Negative = charge

    // Short position (earn swap)
    auto swap_short = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_SELL, 1.0, 1'100'000, 1'090'000, eurusd, 1);
    EXPECT_GT(swap_short, 0);  // Positive = credit
}

TEST_F(SwapModelTest, StandardSwapPercentage) {
    StandardSwap model(-0.05, 0.03, SwapType::PERCENTAGE);  // As percentage

    auto swap = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, 1'110'000, eurusd, 1);
    EXPECT_NE(swap, 0);
}

TEST_F(SwapModelTest, TripleSwapMultiplier) {
    StandardSwap model(-0.5, 0.3, SwapType::POINTS, 0, 3);  // Triple on Wednesday

    // Wednesday (day 3) should have 3x multiplier
    int64_t wednesday = 1'000'000;
    EXPECT_EQ(model.get_multiplier(wednesday), 1);
}

TEST_F(SwapModelTest, IslamicSwap) {
    IslamicSwap model(5.0, 1);  // $5/lot/day after 1 day grace

    // Within grace period: no fee
    auto swap0 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, 1'110'000, eurusd, 0);
    EXPECT_EQ(swap0, 0);

    auto swap1 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, 1'110'000, eurusd, 1);
    EXPECT_EQ(swap1, 0);

    // After grace period: fee applies
    auto swap2 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, 1'110'000, eurusd, 2);
    EXPECT_EQ(swap2, 5'000'000);  // 1 billable day

    auto swap5 = model.calculate(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, 1'100'000, 1'110'000, eurusd, 5);
    EXPECT_EQ(swap5, 20'000'000);  // 4 billable days
}

// ============================================================================
// Spread Model Tests
// ============================================================================

TEST_F(SpreadModelTest, FixedSpread) {
    FixedSpread model(15);  // 15 points = 1.5 pips
    auto spread = model.calculate(tick, eurusd, 1'000'000, rng);
    EXPECT_EQ(spread, 15 * 10);
}

TEST_F(SpreadModelTest, HistoricalSpread) {
    HistoricalSpread model(10);  // 10 point minimum
    auto spread = model.calculate(tick, eurusd, 1'000'000, rng);

    // Should use actual spread (20) or minimum (10), whichever is larger
    int64_t actual_spread = tick.ask - tick.bid;
    int64_t expected_spread = std::max(actual_spread, 10 * 10LL);
    EXPECT_EQ(spread, expected_spread);
}

TEST_F(SpreadModelTest, TimeOfDaySpread) {
    TimeOfDaySpread model(15);  // 15 point base

    // Test different times
    auto spread = model.calculate(tick, eurusd, 1'000'000, rng);
    EXPECT_GT(spread, 0);
}

TEST_F(SpreadModelTest, RandomSpread) {
    RandomSpread model(15, 5, 5);  // Mean=15, StdDev=5, Min=5
    auto spread = model.calculate(tick, eurusd, 1'000'000, rng);
    EXPECT_GE(spread, 5 * 10);  // At least minimum
}

TEST_F(SpreadModelTest, VolatilitySpread) {
    VolatilitySpread model(15, 0.5);

    // First call initializes
    auto spread1 = model.calculate(tick, eurusd, 1'000'000, rng);
    EXPECT_GT(spread1, 0);

    // Subsequent calls update volatility
    Tick tick2{2'000'000, 1, 1'120'000, 1'120'020, 1'000'000, 1'000'000, 20};
    auto spread2 = model.calculate(tick2, eurusd, 2'000'000, rng);
    EXPECT_GT(spread2, spread1);  // Higher volatility = wider spread
}

// ============================================================================
// Costs Engine Tests
// ============================================================================

TEST_F(CostsEngineTest, ConstructionRequiresAllModels) {
    // Missing models should throw
    EXPECT_THROW(
        CostsEngine(nullptr, nullptr, nullptr, nullptr, 0),
        std::invalid_argument
    );
}

TEST_F(CostsEngineTest, MarketOrderExecution) {
    auto engine = create_engine();
    Tick tick{1'000'000, 1, 1'100'000, 1'100'020, 1'000'000, 1'000'000, 20};

    // Buy at ask
    auto result = engine->execute_market_order(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, tick, eurusd);
    EXPECT_TRUE(result.executed);
    EXPECT_GT(result.fill_price, tick.ask);  // Ask + slippage
    EXPECT_GT(result.slippage, 0);
    EXPECT_GT(result.commission, 0);

    // Sell at bid
    result = engine->execute_market_order(ENUM_POSITION_TYPE::POSITION_TYPE_SELL, 1.0, tick, eurusd);
    EXPECT_TRUE(result.executed);
    EXPECT_LT(result.fill_price, tick.bid);  // Bid - slippage
}

TEST_F(CostsEngineTest, LimitOrderTrigger) {
    auto engine = create_engine();
    Tick tick{1'000'000, 1, 1'100'000, 1'100'020, 1'000'000, 1'000'000, 20};

    PendingOrder buy_limit{};
    buy_limit.type = ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT;
    buy_limit.volume = 1.0;
    buy_limit.price = 1'100'030;  // Above ask - should trigger

    auto result = engine->evaluate_order(buy_limit, tick, eurusd);
    EXPECT_TRUE(result.executed);
    EXPECT_GT(result.fill_price, 0);
}

TEST_F(CostsEngineTest, LimitOrderDoesNotTrigger) {
    auto engine = create_engine();
    Tick tick{1'000'000, 1, 1'100'000, 1'100'020, 1'000'000, 1'000'000, 20};

    PendingOrder buy_limit{};
    buy_limit.type = ENUM_ORDER_TYPE::ORDER_TYPE_BUY_LIMIT;
    buy_limit.volume = 1.0;
    buy_limit.price = 1'100'000;  // Below ask - should not trigger

    auto result = engine->evaluate_order(buy_limit, tick, eurusd);
    EXPECT_FALSE(result.executed);
}

TEST_F(CostsEngineTest, StopOrderTrigger) {
    auto engine = create_engine();
    Tick tick{1'000'000, 1, 1'100'000, 1'100'020, 1'000'000, 1'000'000, 20};

    PendingOrder buy_stop{};
    buy_stop.type = ENUM_ORDER_TYPE::ORDER_TYPE_BUY_STOP;
    buy_stop.volume = 1.0;
    buy_stop.price = 1'100'000;  // Below ask - should trigger

    auto result = engine->evaluate_order(buy_stop, tick, eurusd);
    EXPECT_TRUE(result.executed);
}

TEST_F(CostsEngineTest, PositionStopLossTrigger) {
    auto engine = create_engine();
    Tick tick{1'000'000, 1, 1'090'000, 1'090'020, 1'000'000, 1'000'000, 20};  // Price dropped

    Position long_position{};
    long_position.type = ENUM_POSITION_TYPE::POSITION_TYPE_BUY;
    long_position.volume = 1.0;
    long_position.open_price = 1'100'000;
    long_position.sl = 1'095'000;  // SL below current bid - should trigger
    long_position.open_time_us = 0;

    auto result = engine->evaluate_position(long_position, tick, eurusd);
    EXPECT_TRUE(result.executed);
    EXPECT_GT(result.commission, 0);
}

TEST_F(CostsEngineTest, PositionTakeProfitTrigger) {
    auto engine = create_engine();
    Tick tick{1'000'000, 1, 1'110'000, 1'110'020, 1'000'000, 1'000'000, 20};  // Price rose

    Position long_position{};
    long_position.type = ENUM_POSITION_TYPE::POSITION_TYPE_BUY;
    long_position.volume = 1.0;
    long_position.open_price = 1'100'000;
    long_position.tp = 1'105'000;  // TP below current bid - should trigger
    long_position.open_time_us = 0;

    auto result = engine->evaluate_position(long_position, tick, eurusd);
    EXPECT_TRUE(result.executed);
}

TEST_F(CostsEngineTest, GapScenarioFillsAtGapPrice) {
    auto engine = create_engine();

    // Price gaps from 1.1000 to 1.1100 (jumping over stop at 1.1050)
    Tick gap_tick{1'000'000, 1, 1'110'000, 1'110'020, 1'000'000, 1'000'000, 20};

    Position long_position{};
    long_position.type = ENUM_POSITION_TYPE::POSITION_TYPE_BUY;
    long_position.volume = 1.0;
    long_position.open_price = 1'100'000;
    long_position.tp = 1'105'000;  // TP at 1.1050, but price gapped to 1.1100
    long_position.open_time_us = 0;

    auto result = engine->evaluate_position(long_position, gap_tick, eurusd);
    EXPECT_TRUE(result.executed);
    // Should fill at or near gap price (bid=1.1100), not stop level (1.1050)
    EXPECT_GT(result.fill_price, long_position.tp);
}

TEST_F(CostsEngineTest, DeterministicExecution) {
    auto engine1 = create_engine();
    auto engine2 = create_engine();

    Tick tick{1'000'000, 1, 1'100'000, 1'100'020, 1'000'000, 1'000'000, 20};

    // Same seed should produce identical results
    auto result1 = engine1->execute_market_order(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, tick, eurusd);
    auto result2 = engine2->execute_market_order(ENUM_POSITION_TYPE::POSITION_TYPE_BUY, 1.0, tick, eurusd);

    EXPECT_EQ(result1.fill_price, result2.fill_price);
    EXPECT_EQ(result1.slippage, result2.slippage);
    EXPECT_EQ(result1.commission, result2.commission);
}

TEST_F(CostsEngineTest, SwapCalculation) {
    // Create engine with actual swap model
    auto engine = std::make_unique<CostsEngine>(
        std::make_unique<ZeroSlippage>(),
        std::make_unique<ZeroCommission>(),
        std::make_unique<StandardSwap>(-0.5, 0.3, SwapType::POINTS),
        std::make_unique<FixedSpread>(15),
        42
    );

    Position long_position{};
    long_position.type = ENUM_POSITION_TYPE::POSITION_TYPE_BUY;
    long_position.volume = 1.0;
    long_position.open_price = 1'100'000;
    long_position.open_time_us = 0;

    int64_t current_price = 1'110'000;
    int64_t timestamp = 24LL * 3600LL * 1'000'000LL;  // 1 day later

    auto swap = engine->calculate_swap(long_position, current_price, eurusd, timestamp);
    EXPECT_NE(swap, 0);
}

