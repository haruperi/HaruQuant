/**
 * @file bench_event_loop.cpp
 * @brief Performance benchmarks for EventLoop
 *
 * Target: ≥1M ticks/second throughput
 */

#include <benchmark/benchmark.h>
#include "engine/event_loop.hpp"
#include "engine/global_clock.hpp"
#include <random>

using namespace hqt;

// ============================================================================
// EventLoop Throughput Benchmarks
// ============================================================================

/**
 * @brief Benchmark pure event processing (no work in handler)
 */
static void BM_EventLoop_PureProcessing(benchmark::State& state) {
    const int64_t num_events = state.range(0);

    for (auto _ : state) {
        EventLoop loop;

        // Push events
        state.PauseTiming();
        for (int64_t i = 0; i < num_events; ++i) {
            loop.push(Event::tick(i * 1000, 1));
        }
        state.ResumeTiming();

        // Process events
        loop.run([](const Event&) {
            // Minimal work - just process
        });

        state.SetItemsProcessed(num_events);
    }
}
BENCHMARK(BM_EventLoop_PureProcessing)
    ->Arg(1000)
    ->Arg(10000)
    ->Arg(100000)
    ->Arg(1000000)
    ->Unit(benchmark::kMillisecond);

/**
 * @brief Benchmark with realistic handler work (timestamp tracking)
 */
static void BM_EventLoop_WithTimestampTracking(benchmark::State& state) {
    const int64_t num_events = state.range(0);

    for (auto _ : state) {
        EventLoop loop;

        // Push events
        state.PauseTiming();
        for (int64_t i = 0; i < num_events; ++i) {
            loop.push(Event::tick(i * 1000, 1));
        }
        state.ResumeTiming();

        int64_t last_timestamp = 0;
        loop.run([&last_timestamp](const Event& e) {
            last_timestamp = e.timestamp_us;
        });

        state.SetItemsProcessed(num_events);
        benchmark::DoNotOptimize(last_timestamp);
    }
}
BENCHMARK(BM_EventLoop_WithTimestampTracking)
    ->Arg(1000)
    ->Arg(10000)
    ->Arg(100000)
    ->Arg(1000000)
    ->Unit(benchmark::kMillisecond);

/**
 * @brief Benchmark with GlobalClock updates
 */
static void BM_EventLoop_WithGlobalClock(benchmark::State& state) {
    const int64_t num_events = state.range(0);

    for (auto _ : state) {
        EventLoop loop;
        GlobalClock clock;

        // Push events
        state.PauseTiming();
        for (int64_t i = 0; i < num_events; ++i) {
            loop.push(Event::tick(i * 1000, 1));
        }
        state.ResumeTiming();

        loop.run([&clock](const Event& e) {
            if (e.type == EventType::TICK) {
                clock.update_symbol(e.data.tick_data.symbol_id, e.timestamp_us);
            }
        });

        state.SetItemsProcessed(num_events);
    }
}
BENCHMARK(BM_EventLoop_WithGlobalClock)
    ->Arg(1000)
    ->Arg(10000)
    ->Arg(100000)
    ->Arg(1000000)
    ->Unit(benchmark::kMillisecond);

/**
 * @brief Benchmark multi-asset scenario (3 symbols)
 */
static void BM_EventLoop_MultiAsset(benchmark::State& state) {
    const int64_t num_events = state.range(0);
    const int num_symbols = 3;

    for (auto _ : state) {
        EventLoop loop;
        GlobalClock clock;

        // Push interleaved events for 3 symbols
        state.PauseTiming();
        std::mt19937_64 rng(12345);
        std::uniform_int_distribution<uint32_t> symbol_dist(1, num_symbols);

        for (int64_t i = 0; i < num_events; ++i) {
            uint32_t symbol_id = symbol_dist(rng);
            loop.push(Event::tick(i * 1000, symbol_id));
        }
        state.ResumeTiming();

        loop.run([&clock](const Event& e) {
            if (e.type == EventType::TICK) {
                clock.update_symbol(e.data.tick_data.symbol_id, e.timestamp_us);
            }
        });

        state.SetItemsProcessed(num_events);
    }
}
BENCHMARK(BM_EventLoop_MultiAsset)
    ->Arg(1000)
    ->Arg(10000)
    ->Arg(100000)
    ->Arg(1000000)
    ->Unit(benchmark::kMillisecond);

/**
 * @brief Benchmark push performance
 */
static void BM_EventLoop_PushOnly(benchmark::State& state) {
    const int64_t num_events = state.range(0);

    for (auto _ : state) {
        EventLoop loop;

        for (int64_t i = 0; i < num_events; ++i) {
            loop.push(Event::tick(i * 1000, 1));
        }

        state.SetItemsProcessed(num_events);
    }
}
BENCHMARK(BM_EventLoop_PushOnly)
    ->Arg(1000)
    ->Arg(10000)
    ->Arg(100000)
    ->Arg(1000000)
    ->Unit(benchmark::kMillisecond);

/**
 * @brief Benchmark batch push performance
 */
static void BM_EventLoop_PushBatch(benchmark::State& state) {
    const int64_t num_events = state.range(0);

    for (auto _ : state) {
        EventLoop loop;

        state.PauseTiming();
        std::vector<Event> events;
        events.reserve(num_events);
        for (int64_t i = 0; i < num_events; ++i) {
            events.push_back(Event::tick(i * 1000, 1));
        }
        state.ResumeTiming();

        loop.push_batch(events);

        state.SetItemsProcessed(num_events);
    }
}
BENCHMARK(BM_EventLoop_PushBatch)
    ->Arg(1000)
    ->Arg(10000)
    ->Arg(100000)
    ->Arg(1000000)
    ->Unit(benchmark::kMillisecond);

/**
 * @brief Benchmark step() operation
 */
static void BM_EventLoop_Step(benchmark::State& state) {
    const int64_t events_per_step = state.range(0);

    for (auto _ : state) {
        EventLoop loop;

        // Fill queue with many events
        state.PauseTiming();
        for (int64_t i = 0; i < events_per_step * 10; ++i) {
            loop.push(Event::tick(i * 1000, 1));
        }
        state.ResumeTiming();

        int64_t dummy = 0;
        loop.step(events_per_step, [&dummy](const Event& e) {
            dummy += e.timestamp_us;
        });

        state.SetItemsProcessed(events_per_step);
        benchmark::DoNotOptimize(dummy);
    }
}
BENCHMARK(BM_EventLoop_Step)
    ->Arg(1)
    ->Arg(10)
    ->Arg(100)
    ->Arg(1000)
    ->Unit(benchmark::kMicrosecond);

// ============================================================================
// GlobalClock Benchmarks
// ============================================================================

/**
 * @brief Benchmark GlobalClock update performance
 */
static void BM_GlobalClock_UpdateSingle(benchmark::State& state) {
    GlobalClock clock;
    int64_t timestamp = 1000000;

    for (auto _ : state) {
        clock.update_symbol(1, timestamp);
        timestamp += 1000;
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_GlobalClock_UpdateSingle);

/**
 * @brief Benchmark GlobalClock with multiple symbols
 */
static void BM_GlobalClock_MultiSymbol(benchmark::State& state) {
    const int64_t num_symbols = state.range(0);
    GlobalClock clock;

    // Initialize symbols
    for (int64_t i = 1; i <= num_symbols; ++i) {
        clock.update_symbol(static_cast<uint32_t>(i), 1000000);
    }

    int64_t timestamp = 1000000;

    for (auto _ : state) {
        // Update a random symbol
        uint32_t symbol_id = static_cast<uint32_t>((timestamp % num_symbols) + 1);
        clock.update_symbol(symbol_id, timestamp);
        timestamp += 1000;
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_GlobalClock_MultiSymbol)
    ->Arg(1)
    ->Arg(3)
    ->Arg(10)
    ->Arg(50);

/**
 * @brief Benchmark can_advance() checks
 */
static void BM_GlobalClock_CanAdvance(benchmark::State& state) {
    const int64_t num_symbols = state.range(0);
    GlobalClock clock;

    // Initialize symbols
    for (int64_t i = 1; i <= num_symbols; ++i) {
        clock.update_symbol(static_cast<uint32_t>(i), 1000000 + i * 1000);
    }

    int64_t query_timestamp = 1005000;

    for (auto _ : state) {
        bool can_advance = clock.can_advance(1, query_timestamp);
        benchmark::DoNotOptimize(can_advance);
        query_timestamp += 100;
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_GlobalClock_CanAdvance)
    ->Arg(1)
    ->Arg(3)
    ->Arg(10)
    ->Arg(50);

/**
 * @brief Benchmark PITEnforcer clamp operations
 */
static void BM_PITEnforcer_Clamp(benchmark::State& state) {
    GlobalClock clock;
    clock.update_symbol(1, 1000000);
    clock.update_symbol(2, 999000);

    PITEnforcer enforcer(clock);
    int64_t query_time = 1001000;

    for (auto _ : state) {
        int64_t clamped = enforcer.clamp_query_time(query_time);
        benchmark::DoNotOptimize(clamped);
        query_time += 100;
    }

    state.SetItemsProcessed(state.iterations());
}
BENCHMARK(BM_PITEnforcer_Clamp);

// ============================================================================
// Main
// ============================================================================

BENCHMARK_MAIN();
