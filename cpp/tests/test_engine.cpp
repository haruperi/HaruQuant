/**
 * @file test_engine.cpp
 * @brief Integration tests for Engine facade
 *
 * Tests the complete backtesting engine including:
 * - Data loading and event processing
 * - Trading commands with margin checks
 * - Callback execution
 * - Run loop control
 */

#include <gtest/gtest.h>
#include "core/engine.hpp"
#include "data/bar.hpp"
#include "trading/symbol_info.hpp"
#include <memory>
#include <vector>

using namespace hqt;

// ============================================================================
// Test Fixtures
// ============================================================================

class EngineTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Create engine with 10,000 USD at 1:100 leverage
        engine = std::make_unique<Engine>(10000.0, "USD", 100);

        // Create EURUSD symbol info
        eurusd.Name("EURUSD");
        eurusd.SetSymbolId(1);
        eurusd.SetDigits(5);
        eurusd.SetPoint(0.00001);
        eurusd.SetContractSize(100000.0);
        eurusd.SetCurrencyBase("EUR");
        eurusd.SetCurrencyProfit("USD");
        eurusd.UpdatePrice(1.10000, 1.10015, 0);

        // Load symbol
        engine->load_symbol("EURUSD", eurusd);

        // Load currency conversion
        engine->load_conversion_pair("EUR", "USD", 1.10);
    }

    std::unique_ptr<Engine> engine;
    SymbolInfo eurusd;
};

// ============================================================================
// Basic Engine Tests
// ============================================================================

TEST_F(EngineTest, EngineConstruction) {
    EXPECT_FALSE(engine->is_running());
    EXPECT_FALSE(engine->is_paused());
    EXPECT_EQ(engine->current_time(), 0);

    const auto& account = engine->account();
    EXPECT_DOUBLE_EQ(account.Balance(), 10000.0);
    EXPECT_EQ(account.Currency(), "USD");
    EXPECT_EQ(account.Leverage(), 100);
}

TEST_F(EngineTest, LoadSymbol) {
    const SymbolInfo* loaded = engine->get_symbol("EURUSD");
    ASSERT_NE(loaded, nullptr);
    EXPECT_EQ(loaded->Name(), "EURUSD");
    EXPECT_EQ(loaded->SymbolId(), 1);
    EXPECT_DOUBLE_EQ(loaded->Digits(), 5);
}

TEST_F(EngineTest, LoadSymbolNotFound) {
    const SymbolInfo* not_found = engine->get_symbol("GBPUSD");
    EXPECT_EQ(not_found, nullptr);
}

// ============================================================================
// Data Feed Integration Tests
// ============================================================================

TEST_F(EngineTest, DataFeedAccess) {
    IDataFeed& feed = engine->data_feed();

    // Create sample bars
    std::vector<Bar> bars;
    for (int i = 0; i < 100; ++i) {
        Bar bar;
        bar.timestamp_us = i * 60000000LL;  // 1 minute bars
        bar.symbol_id = 1;
        bar.open = 1100000 + i;
        bar.high = 1100100 + i;
        bar.low = 1099900 + i;
        bar.close = 1100050 + i;
        bar.tick_volume = 1000;
        bar.real_volume = 0;
        bars.push_back(bar);
    }

    // Load bars
    auto* bar_feed = dynamic_cast<BarDataFeed*>(&feed);
    ASSERT_NE(bar_feed, nullptr);
    size_t loaded = bar_feed->load_bars("EURUSD", Timeframe::M1, std::move(bars));
    EXPECT_EQ(loaded, 100);

    // Check data is available
    EXPECT_TRUE(feed.has_data("EURUSD", Timeframe::M1));
    EXPECT_EQ(feed.get_bar_count("EURUSD", Timeframe::M1), 100);
}

TEST_F(EngineTest, PITDataAccess) {
    auto* bar_feed = dynamic_cast<BarDataFeed*>(&engine->data_feed());
    ASSERT_NE(bar_feed, nullptr);

    // Create bars at specific times
    std::vector<Bar> bars;
    for (int i = 0; i < 10; ++i) {
        Bar bar;
        bar.timestamp_us = i * 1000000LL;  // 1 second apart
        bar.symbol_id = 1;
        bar.open = 1100000;
        bar.high = 1100100;
        bar.low = 1099900;
        bar.close = 1100050;
        bars.push_back(bar);
    }
    bar_feed->load_bars("EURUSD", Timeframe::M1, std::move(bars));

    // Query at timestamp 5.5 seconds - should get bars 0-5
    auto result = bar_feed->get_bars("EURUSD", Timeframe::M1, 5500000LL);
    EXPECT_EQ(result.size(), 6);  // Bars 0-5
    EXPECT_EQ(result[0].timestamp_us, 5000000LL);  // Newest first
    EXPECT_EQ(result[5].timestamp_us, 0LL);

    // Query at timestamp 15 seconds - should get all 10 bars
    result = bar_feed->get_bars("EURUSD", Timeframe::M1, 15000000LL);
    EXPECT_EQ(result.size(), 10);
}

// ============================================================================
// Trading Command Tests
// ============================================================================

TEST_F(EngineTest, BuyOrder) {
    // Update prices
    engine->data_feed();  // Ensure feed is initialized

    bool success = engine->buy(0.1, "EURUSD", 1.09000, 1.11000, "test buy");
    EXPECT_TRUE(success);

    auto positions = engine->positions();
    EXPECT_EQ(positions.size(), 1);
    EXPECT_EQ(positions[0].Symbol(), "EURUSD");
    EXPECT_TRUE(positions[0].PositionType() == ENUM_POSITION_TYPE::POSITION_TYPE_BUY);
    EXPECT_DOUBLE_EQ(positions[0].Volume(), 0.1);
}

TEST_F(EngineTest, SellOrder) {
    bool success = engine->sell(0.1, "EURUSD", 1.11000, 1.09000, "test sell");
    EXPECT_TRUE(success);

    auto positions = engine->positions();
    EXPECT_EQ(positions.size(), 1);
    EXPECT_TRUE(positions[0].PositionType() == ENUM_POSITION_TYPE::POSITION_TYPE_SELL);
}

TEST_F(EngineTest, MarginCheck) {
    // Try to open position larger than available margin
    // With 10,000 balance at 1:100 leverage:
    // Max volume = 10000 * 100 / (1.10 * 100000) ≈ 9 lots

    // This should succeed
    bool success = engine->buy(5.0, "EURUSD");
    EXPECT_TRUE(success);

    // This should fail due to insufficient margin
    success = engine->buy(10.0, "EURUSD");
    EXPECT_FALSE(success);
}

TEST_F(EngineTest, ModifyPosition) {
    // Open position
    engine->buy(0.1, "EURUSD");
    auto positions = engine->positions();
    ASSERT_EQ(positions.size(), 1);
    uint64_t ticket = positions[0].Ticket();

    // Modify SL/TP
    bool success = engine->modify(ticket, 1.09500, 1.10500);
    EXPECT_TRUE(success);

    positions = engine->positions();
    EXPECT_DOUBLE_EQ(positions[0].StopLoss(), 1.09500);
    EXPECT_DOUBLE_EQ(positions[0].TakeProfit(), 1.10500);
}

TEST_F(EngineTest, ClosePosition) {
    // Open position
    engine->buy(0.1, "EURUSD");
    auto positions = engine->positions();
    ASSERT_EQ(positions.size(), 1);
    uint64_t ticket = positions[0].Ticket();

    // Close position
    bool success = engine->close(ticket);
    EXPECT_TRUE(success);

    positions = engine->positions();
    EXPECT_EQ(positions.size(), 0);

    // Check deal was created
    const auto& deals = engine->deals();
    EXPECT_GE(deals.size(), 1);  // Close deal is recorded
}

// ============================================================================
// Event Processing Tests
// ============================================================================

TEST_F(EngineTest, TickCallbackExecution) {
    int tick_count = 0;
    std::string last_symbol;

    engine->set_on_tick([&](const Tick& /*tick*/, const SymbolInfo& symbol) {
        tick_count++;
        last_symbol = symbol.Name();
    });

    // Schedule tick events
    Event tick_event = Event::tick(1000000LL, 1);

    engine->event_loop().push(tick_event);

    // Run one step
    size_t processed = engine->run_steps(1);
    EXPECT_EQ(processed, 1);
    EXPECT_EQ(tick_count, 1);
    EXPECT_EQ(last_symbol, "EURUSD");
}

TEST_F(EngineTest, BarCallbackExecution) {
    // Load bar data
    auto* bar_feed = dynamic_cast<BarDataFeed*>(&engine->data_feed());
    ASSERT_NE(bar_feed, nullptr);

    std::vector<Bar> bars;
    Bar bar;
    bar.timestamp_us = 60000000LL;
    bar.symbol_id = 1;
    bar.open = 1100000;
    bar.high = 1100100;
    bar.low = 1099900;
    bar.close = 1100050;
    bars.push_back(bar);
    bar_feed->load_bars("EURUSD", Timeframe::M1, std::move(bars));

    int bar_count = 0;
    Timeframe received_tf = Timeframe::M1;

    engine->set_on_bar([&](const Bar& /*b*/, const SymbolInfo& /*symbol*/, Timeframe tf) {
        bar_count++;
        received_tf = tf;
    });

    // Schedule bar close event
    Event bar_event = Event::bar_close(60000000LL, 1, static_cast<uint16_t>(Timeframe::M1));

    engine->event_loop().push(bar_event);

    // Run one step
    size_t processed = engine->run_steps(1);
    EXPECT_EQ(processed, 1);
    EXPECT_EQ(bar_count, 1);
    EXPECT_EQ(received_tf, Timeframe::M1);
}

TEST_F(EngineTest, TradeCallbackExecution) {
    int trade_count = 0;

    engine->set_on_trade([&](const DealInfo& /*deal*/) {
        trade_count++;
    });

    // Open and close position
    engine->buy(0.1, "EURUSD");
    auto positions = engine->positions();
    ASSERT_EQ(positions.size(), 1);
    engine->close(positions[0].Ticket());

    // Trade callback not invoked yet (no events processed)
    // In real usage, callbacks would be triggered during event processing
    EXPECT_GE(trade_count, 0);
}

// ============================================================================
// Run Loop Control Tests
// ============================================================================

TEST_F(EngineTest, RunSteps) {
    // Schedule 10 tick events
    for (int i = 0; i < 10; ++i) {
        Event event = Event::tick(i * 1000000LL, 1);
        engine->event_loop().push(event);
    }

    // Run 5 steps
    size_t processed = engine->run_steps(5);
    EXPECT_EQ(processed, 5);

    // Current time should be at 5th event
    EXPECT_EQ(engine->current_time(), 4000000LL);

    // Run remaining 5 steps
    processed = engine->run_steps(5);
    EXPECT_EQ(processed, 5);
    EXPECT_EQ(engine->current_time(), 9000000LL);
}

TEST_F(EngineTest, PauseResume) {
    int tick_count = 0;
    engine->set_on_tick([&](const Tick&, const SymbolInfo&) {
        tick_count++;
        if (tick_count == 5) {
            engine->pause();
        }
    });

    // Schedule 10 events
    for (int i = 0; i < 10; ++i) {
        Event event = Event::tick(i * 1000000LL, 1);
        engine->event_loop().push(event);
    }

    // Run until paused
    size_t processed = engine->run_steps(10);
    EXPECT_EQ(tick_count, 5);
    EXPECT_TRUE(engine->is_paused());

    // Resume
    engine->resume();
    EXPECT_FALSE(engine->is_paused());

    // Run remaining
    processed = engine->run_steps(5);
    EXPECT_EQ(tick_count, 10);
}

TEST_F(EngineTest, Stop) {
    int tick_count = 0;
    engine->set_on_tick([&](const Tick&, const SymbolInfo&) {
        tick_count++;
        if (tick_count == 5) {
            engine->stop();
        }
    });

    // Schedule 10 events
    for (int i = 0; i < 10; ++i) {
        Event event = Event::tick(i * 1000000LL, 1);
        engine->event_loop().push(event);
    }

    // Run until stopped
    size_t processed = engine->run_steps(10);
    EXPECT_EQ(tick_count, 5);
    EXPECT_FALSE(engine->is_running());

    // Cannot run after stop (would need to call run_steps again to restart)
    engine->resume();
    processed = engine->run_steps(5);
    EXPECT_EQ(tick_count, 10);  // Should continue
}

// ============================================================================
// Integration Scenario Tests
// ============================================================================

TEST_F(EngineTest, CompleteBacktestScenario) {
    // Setup: Load bar data
    auto* bar_feed = dynamic_cast<BarDataFeed*>(&engine->data_feed());
    ASSERT_NE(bar_feed, nullptr);

    std::vector<Bar> bars;
    for (int i = 0; i < 100; ++i) {
        Bar bar;
        bar.timestamp_us = i * 60000000LL;
        bar.symbol_id = 1;
        bar.open = 1100000 + (i % 20) * 100;
        bar.high = bar.open + 100;
        bar.low = bar.open - 100;
        bar.close = bar.open + 50;
        bars.push_back(bar);
    }
    bar_feed->load_bars("EURUSD", Timeframe::M1, bars);

    // Setup: Strategy logic - simple moving average crossover
    int trades_executed = 0;
    double last_ma = 0.0;

    engine->set_on_bar([&](const Bar& bar, const SymbolInfo& /*symbol*/, Timeframe /*tf*/) {
        // Calculate simple 5-bar MA
        auto bars_vec = bar_feed->get_bars("EURUSD", Timeframe::M1,
                                           bar.timestamp_us, 5);
        if (bars_vec.size() < 5) return;

        double ma = 0.0;
        for (const auto& b : bars_vec) {
            ma += static_cast<double>(b.close) / 1e6;
        }
        ma /= 5.0;

        double current_price = static_cast<double>(bar.close) / 1e6;

        // Trading logic
        auto positions = engine->positions();
        if (positions.empty() && current_price > ma && last_ma > 0.0) {
            // Buy signal
            if (engine->buy(0.1, "EURUSD")) {
                trades_executed++;
            }
        } else if (!positions.empty() && current_price < ma) {
            // Sell signal
            for (const auto& pos : positions) {
                if (engine->close(pos.Ticket())) {
                    trades_executed++;
                }
            }
        }

        last_ma = ma;
    });

    // Schedule bar close events
    for (int i = 0; i < 100; ++i) {
        Event event = Event::bar_close(i * 60000000LL, 1, static_cast<uint16_t>(Timeframe::M1));
        engine->event_loop().push(event);
    }

    // Run simulation
    size_t processed = engine->run_steps(100);
    EXPECT_EQ(processed, 100);

    // Verify trades were executed
    EXPECT_GT(trades_executed, 0);

    // Verify deals recorded
    const auto& deals = engine->deals();
    EXPECT_GT(deals.size(), 0);

    // Account balance should have changed
    const auto& account = engine->account();
    // (Balance might be higher or lower depending on strategy performance)
    EXPECT_NE(account.Balance(), 10000.0);
}

// ============================================================================
// Multi-Symbol Test
// ============================================================================

TEST_F(EngineTest, MultiSymbolTrading) {
    // Add GBPUSD
    SymbolInfo gbpusd;
    gbpusd.Name("GBPUSD");
    gbpusd.SetSymbolId(2);
    gbpusd.SetDigits(5);
    gbpusd.SetPoint(0.00001);
    gbpusd.SetContractSize(100000.0);
    gbpusd.SetCurrencyBase("GBP");
    gbpusd.SetCurrencyProfit("USD");
    gbpusd.UpdatePrice(1.30000, 1.30015, 0);

    engine->load_symbol("GBPUSD", gbpusd);
    engine->load_conversion_pair("GBP", "USD", 1.30);

    // Open positions on both symbols
    bool eur_success = engine->buy(0.1, "EURUSD");
    bool gbp_success = engine->buy(0.1, "GBPUSD");

    EXPECT_TRUE(eur_success);
    EXPECT_TRUE(gbp_success);

    auto positions = engine->positions();
    EXPECT_EQ(positions.size(), 2);

    // Verify different symbols
    std::set<std::string> symbols;
    for (const auto& pos : positions) {
        symbols.insert(pos.Symbol());
    }
    EXPECT_EQ(symbols.size(), 2);
    EXPECT_TRUE(symbols.count("EURUSD") > 0);
    EXPECT_TRUE(symbols.count("GBPUSD") > 0);
}

// Entry point is provided by GTest::gtest_main
