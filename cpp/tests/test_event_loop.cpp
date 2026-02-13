/**
 * @file test_event_loop.cpp
 * @brief Unit tests for EventLoop and GlobalClock
 */

#include <gtest/gtest.h>
#include "engine/event_loop.hpp"
#include "engine/global_clock.hpp"
#include "data/bar.hpp"
#include <vector>
#include <atomic>
#include <thread>
#include <chrono>

using namespace hqt;

// ============================================================================
// EventLoop Tests
// ============================================================================

TEST(EventLoopTest, DefaultConstruction) {
    EventLoop loop;
    EXPECT_TRUE(loop.empty());
    EXPECT_EQ(loop.size(), 0);
    EXPECT_FALSE(loop.is_running());
    EXPECT_FALSE(loop.is_paused());
    EXPECT_FALSE(loop.is_stopped());
    EXPECT_EQ(loop.events_processed(), 0);
    EXPECT_EQ(loop.current_timestamp(), 0);
}

TEST(EventLoopTest, PushSingleEvent) {
    EventLoop loop;
    loop.push(Event::tick(1000000, 1));

    EXPECT_FALSE(loop.empty());
    EXPECT_EQ(loop.size(), 1);
}

TEST(EventLoopTest, PushMultipleEvents) {
    EventLoop loop;
    loop.push(Event::tick(1000000, 1));
    loop.push(Event::tick(2000000, 1));
    loop.push(Event::tick(3000000, 1));

    EXPECT_EQ(loop.size(), 3);
}

TEST(EventLoopTest, ChronologicalOrdering) {
    EventLoop loop;

    // Push events out of order
    loop.push(Event::tick(3000000, 1));
    loop.push(Event::tick(1000000, 1));
    loop.push(Event::tick(2000000, 1));

    // Collect processed event timestamps
    std::vector<int64_t> timestamps;
    loop.run([&timestamps](const Event& e) {
        timestamps.push_back(e.timestamp_us);
    });

    // Should be processed in chronological order
    ASSERT_EQ(timestamps.size(), 3);
    EXPECT_EQ(timestamps[0], 1000000);
    EXPECT_EQ(timestamps[1], 2000000);
    EXPECT_EQ(timestamps[2], 3000000);
}

TEST(EventLoopTest, ProcessAllEvents) {
    EventLoop loop;

    for (int64_t i = 1; i <= 100; ++i) {
        loop.push(Event::tick(i * 1000, 1));
    }

    int count = 0;
    loop.run([&count](const Event&) {
        ++count;
    });

    EXPECT_EQ(count, 100);
    EXPECT_EQ(loop.events_processed(), 100);
    EXPECT_TRUE(loop.empty());
}

TEST(EventLoopTest, CurrentTimestampTracking) {
    EventLoop loop;

    loop.push(Event::tick(1000000, 1));
    loop.push(Event::tick(2000000, 1));

    int64_t last_timestamp = 0;
    loop.run([&](const Event&) {
        last_timestamp = loop.current_timestamp();
    });

    EXPECT_EQ(last_timestamp, 2000000);
    EXPECT_EQ(loop.current_timestamp(), 2000000);
}

TEST(EventLoopTest, StopEarly) {
    EventLoop loop;

    for (int64_t i = 1; i <= 100; ++i) {
        loop.push(Event::tick(i * 1000, 1));
    }

    std::atomic<int> count{0};
    std::thread runner([&]() {
        loop.run([&](const Event&) {
            ++count;
            if (count == 10) {
                loop.stop();
            }
        });
    });

    runner.join();

    // Should have processed at least 10 events before stopping
    // (might process a few more due to timing)
    EXPECT_GE(count, 10);
    EXPECT_LT(count, 100);
    EXPECT_TRUE(loop.is_stopped());
}

TEST(EventLoopTest, StepExactly) {
    EventLoop loop;

    for (int64_t i = 1; i <= 100; ++i) {
        loop.push(Event::tick(i * 1000, 1));
    }

    int count = 0;
    loop.step(10, [&count](const Event&) {
        ++count;
    });

    EXPECT_EQ(count, 10);
    EXPECT_EQ(loop.events_processed(), 10);
    EXPECT_EQ(loop.size(), 90);  // 90 events remaining
}

TEST(EventLoopTest, StepMultipleTimes) {
    EventLoop loop;

    for (int64_t i = 1; i <= 100; ++i) {
        loop.push(Event::tick(i * 1000, 1));
    }

    // Step through events in chunks
    int total = 0;

    loop.step(10, [&total](const Event&) { ++total; });
    EXPECT_EQ(total, 10);

    loop.step(20, [&total](const Event&) { ++total; });
    EXPECT_EQ(total, 30);

    loop.step(70, [&total](const Event&) { ++total; });
    EXPECT_EQ(total, 100);

    EXPECT_TRUE(loop.empty());
}

TEST(EventLoopTest, StepBeyondAvailable) {
    EventLoop loop;

    for (int64_t i = 1; i <= 10; ++i) {
        loop.push(Event::tick(i * 1000, 1));
    }

    int count = 0;
    loop.step(100, [&count](const Event&) {
        ++count;
    });

    // Should only process available events
    EXPECT_EQ(count, 10);
    EXPECT_TRUE(loop.empty());
}

TEST(EventLoopTest, PauseResume) {
    EventLoop loop;

    for (int64_t i = 1; i <= 100; ++i) {
        loop.push(Event::tick(i * 1000, 1));
    }

    std::atomic<int> count{0};
    std::atomic<bool> paused_at_10{false};

    std::thread runner([&]() {
        loop.run([&](const Event&) {
            ++count;
            if (count == 10) {
                loop.pause();
                paused_at_10 = true;
            }
        });
    });

    // Wait for pause
    while (!paused_at_10) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }

    int count_at_pause = count;
    EXPECT_TRUE(loop.is_paused());

    // Wait a bit to ensure it's actually paused
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    EXPECT_EQ(count, count_at_pause);  // Should not have advanced

    // Resume
    loop.resume();

    runner.join();

    // Should have processed all events
    EXPECT_EQ(count, 100);
}

TEST(EventLoopTest, Clear) {
    EventLoop loop;

    for (int64_t i = 1; i <= 100; ++i) {
        loop.push(Event::tick(i * 1000, 1));
    }

    EXPECT_EQ(loop.size(), 100);

    loop.clear();

    EXPECT_TRUE(loop.empty());
    EXPECT_EQ(loop.size(), 0);
    EXPECT_EQ(loop.events_processed(), 0);
    EXPECT_EQ(loop.current_timestamp(), 0);
}

TEST(EventLoopTest, PushBatch) {
    EventLoop loop;

    std::vector<Event> events;
    for (int64_t i = 1; i <= 50; ++i) {
        events.push_back(Event::tick(i * 1000, 1));
    }

    loop.push_batch(events);
    EXPECT_EQ(loop.size(), 50);
}

TEST(EventLoopTest, MixedEventTypes) {
    EventLoop loop;

    loop.push(Event::tick(1000000, 1));
    loop.push(Event::bar_close(2000000, 1, static_cast<uint16_t>(Timeframe::M1)));
    loop.push(Event::order_trigger(3000000, 12345));
    loop.push(Event::timer(4000000, 1));

    std::vector<EventType> types;
    loop.run([&types](const Event& e) {
        types.push_back(e.type);
    });

    ASSERT_EQ(types.size(), 4);
    EXPECT_EQ(types[0], EventType::TICK);
    EXPECT_EQ(types[1], EventType::BAR_CLOSE);
    EXPECT_EQ(types[2], EventType::ORDER_TRIGGER);
    EXPECT_EQ(types[3], EventType::TIMER);
}

TEST(EventLoopTest, EmptyRun) {
    EventLoop loop;

    int count = 0;
    loop.run([&count](const Event&) {
        ++count;
    });

    EXPECT_EQ(count, 0);
}

TEST(EventLoopTest, AlreadyRunningError) {
    EventLoop loop;
    loop.push(Event::tick(1000000, 1));

    // Start first run
    std::thread runner1([&]() {
        loop.run([](const Event&) {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        });
    });

    // Wait to ensure first run started
    std::this_thread::sleep_for(std::chrono::milliseconds(10));

    // Try to start second run - should throw
    EXPECT_THROW(
        loop.run([](const Event&) {}),
        std::runtime_error
    );

    runner1.join();
}

// ============================================================================
// GlobalClock Tests
// ============================================================================

TEST(GlobalClockTest, DefaultConstruction) {
    GlobalClock clock;
    EXPECT_EQ(clock.current_time(), 0);
    EXPECT_EQ(clock.symbol_count(), 0);
}

TEST(GlobalClockTest, SingleSymbolUpdate) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);

    EXPECT_EQ(clock.current_time(), 1000000);
    EXPECT_EQ(clock.get_symbol_time(1), 1000000);
    EXPECT_EQ(clock.symbol_count(), 1);
}

TEST(GlobalClockTest, MultipleSymbolsMinimum) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);  // EURUSD
    clock.update_symbol(2, 999000);   // GBPUSD (slower)
    clock.update_symbol(3, 1001000);  // USDJPY

    // Global time should be minimum
    EXPECT_EQ(clock.current_time(), 999000);
    EXPECT_EQ(clock.get_slowest_symbol(), 2);
}

TEST(GlobalClockTest, SymbolAdvancement) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);

    // Symbol 2 is holding back global time
    EXPECT_EQ(clock.current_time(), 999000);

    // Symbol 2 advances
    clock.update_symbol(2, 1000500);

    // Now global time advances
    EXPECT_EQ(clock.current_time(), 1000000);
}

TEST(GlobalClockTest, CanAdvanceCheck) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);

    // Symbol 1 cannot advance past symbol 2's time (would violate PIT)
    EXPECT_FALSE(clock.can_advance(1, 1001000));

    // Symbol 1 is already ahead, cannot advance further
    EXPECT_FALSE(clock.can_advance(1, 1000000));

    // Symbol 2 can advance up to symbol 1's time
    EXPECT_TRUE(clock.can_advance(2, 1000000));

    // Symbol 2 can advance partway
    EXPECT_TRUE(clock.can_advance(2, 999500));
}

TEST(GlobalClockTest, SingleSymbolCanAlwaysAdvance) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);

    // With only one symbol, can always advance
    EXPECT_TRUE(clock.can_advance(1, 2000000));
    EXPECT_TRUE(clock.can_advance(1, 10000000));
}

TEST(GlobalClockTest, GetSymbolLag) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);
    clock.update_symbol(3, 998000);

    // Global time = 998000 (symbol 3)
    EXPECT_EQ(clock.current_time(), 998000);

    // Symbol 3 has 0 lag (holding back global time)
    EXPECT_EQ(clock.get_symbol_lag(3), 0);

    // Symbol 2 is 1000 us ahead
    EXPECT_EQ(clock.get_symbol_lag(2), 1000);

    // Symbol 1 is 2000 us ahead
    EXPECT_EQ(clock.get_symbol_lag(1), 2000);
}

TEST(GlobalClockTest, RemoveSymbol) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);
    clock.update_symbol(3, 1001000);

    EXPECT_EQ(clock.current_time(), 999000);  // Symbol 2 is slowest

    // Remove symbol 2
    clock.remove_symbol(2);

    // Now symbol 1 is slowest
    EXPECT_EQ(clock.current_time(), 1000000);
    EXPECT_EQ(clock.symbol_count(), 2);
}

TEST(GlobalClockTest, GetAllTimestamps) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);
    clock.update_symbol(3, 1001000);

    auto timestamps = clock.get_all_timestamps();

    EXPECT_EQ(timestamps.size(), 3);
    EXPECT_EQ(timestamps[1], 1000000);
    EXPECT_EQ(timestamps[2], 999000);
    EXPECT_EQ(timestamps[3], 1001000);
}

TEST(GlobalClockTest, UpdateBatch) {
    GlobalClock clock;

    std::unordered_map<uint32_t, int64_t> updates = {
        {1, 1000000},
        {2, 999000},
        {3, 1001000}
    };

    clock.update_batch(updates);

    EXPECT_EQ(clock.symbol_count(), 3);
    EXPECT_EQ(clock.current_time(), 999000);
}

TEST(GlobalClockTest, Clear) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);

    clock.clear();

    EXPECT_EQ(clock.symbol_count(), 0);
    EXPECT_EQ(clock.current_time(), 0);
}

TEST(GlobalClockTest, Reset) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);

    clock.reset(5000000);

    EXPECT_EQ(clock.symbol_count(), 0);
    EXPECT_EQ(clock.current_time(), 5000000);
}

TEST(GlobalClockTest, GetNonExistentSymbol) {
    GlobalClock clock;

    clock.update_symbol(1, 1000000);

    // Query non-existent symbol
    EXPECT_EQ(clock.get_symbol_time(99), 0);
    EXPECT_EQ(clock.get_symbol_lag(99), 0);
}

// ============================================================================
// PITEnforcer Tests
// ============================================================================

TEST(PITEnforcerTest, ClampQueryTime) {
    GlobalClock clock;
    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);

    PITEnforcer enforcer(clock);

    // Query for future time should be clamped to global time (999000)
    EXPECT_EQ(enforcer.clamp_query_time(1001000), 999000);

    // Query for past time should pass through
    EXPECT_EQ(enforcer.clamp_query_time(998000), 998000);

    // Query at global time should pass through
    EXPECT_EQ(enforcer.clamp_query_time(999000), 999000);
}

TEST(PITEnforcerTest, IsValidQuery) {
    GlobalClock clock;
    clock.update_symbol(1, 1000000);

    PITEnforcer enforcer(clock);

    // Past and present are valid
    EXPECT_TRUE(enforcer.is_valid_query(999000));
    EXPECT_TRUE(enforcer.is_valid_query(1000000));

    // Future is invalid
    EXPECT_FALSE(enforcer.is_valid_query(1001000));
}

TEST(PITEnforcerTest, MaxQueryTime) {
    GlobalClock clock;
    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);

    PITEnforcer enforcer(clock);

    EXPECT_EQ(enforcer.max_query_time(), 999000);
}

// ============================================================================
// Integration Tests
// ============================================================================

TEST(IntegrationTest, EventLoopWithGlobalClock) {
    EventLoop loop;
    GlobalClock clock;

    // Simulate multi-asset data feed
    loop.push(Event::tick(1000000, 1));  // EURUSD
    loop.push(Event::tick(999000, 2));   // GBPUSD
    loop.push(Event::tick(1001000, 1));  // EURUSD
    loop.push(Event::tick(1000000, 2));  // GBPUSD

    loop.run([&clock](const Event& e) {
        if (e.type == EventType::TICK) {
            clock.update_symbol(e.data.tick_data.symbol_id, e.timestamp_us);
        }
    });

    // Final global time should be minimum
    EXPECT_EQ(clock.current_time(), 1000000);
    EXPECT_EQ(clock.get_symbol_time(1), 1001000);
    EXPECT_EQ(clock.get_symbol_time(2), 1000000);
}

TEST(IntegrationTest, PITEnforcementInEventLoop) {
    EventLoop loop;
    GlobalClock clock;
    PITEnforcer enforcer(clock);

    // Add events
    loop.push(Event::tick(1000000, 1));
    loop.push(Event::tick(999000, 2));

    std::vector<int64_t> max_query_times;

    loop.run([&](const Event& e) {
        if (e.type == EventType::TICK) {
            clock.update_symbol(e.data.tick_data.symbol_id, e.timestamp_us);
            max_query_times.push_back(enforcer.max_query_time());
        }
    });

    // After first event (999000), max query time = 999000
    // After second event (1000000), max query time = 999000 (symbol 2 at 999000)
    ASSERT_EQ(max_query_times.size(), 2);
    EXPECT_EQ(max_query_times[0], 999000);
    EXPECT_EQ(max_query_times[1], 999000);
}
