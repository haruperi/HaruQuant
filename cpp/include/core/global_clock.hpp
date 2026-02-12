/**
 * @file global_clock.hpp
 * @brief Global clock for multi-asset synchronization
 *
 * Ensures Point-in-Time (PIT) correctness in multi-asset backtesting.
 * Tracks per-symbol timestamps and prevents any symbol from advancing
 * past timestamps other symbols haven't reached yet.
 *
 * Example problem this solves:
 * - EURUSD data available up to 2024-01-15 10:30:00
 * - GBPUSD data available up to 2024-01-15 10:25:00
 * - Strategy should not see EURUSD data past 10:25:00 until GBPUSD catches up
 */

#pragma once

#include <cstdint>
#include <unordered_map>
#include <mutex>
#include <algorithm>
#include <limits>

namespace hqt {

/**
 * @brief Global clock for multi-asset timestamp synchronization
 *
 * Tracks the latest timestamp for each symbol and provides the global
 * minimum timestamp across all symbols. This ensures Point-in-Time (PIT)
 * correctness - strategies cannot access future data for one symbol
 * while other symbols are lagging behind.
 *
 * Thread-safe: All operations are protected by mutex.
 *
 * Example:
 * @code
 * GlobalClock clock;
 *
 * // Update symbol timestamps as data arrives
 * clock.update_symbol(1, 1000000);  // EURUSD at t=1000000
 * clock.update_symbol(2, 999000);   // GBPUSD at t=999000
 *
 * // Global time is the minimum across all symbols
 * assert(clock.current_time() == 999000);  // Held back by GBPUSD
 *
 * // Check if symbol can advance
 * assert(clock.can_advance(1, 1001000) == false);  // No, would exceed global time
 * assert(clock.can_advance(2, 999500) == true);    // Yes, still behind EURUSD
 * @endcode
 */
class GlobalClock {
private:
    // Per-symbol timestamps (symbol_id -> latest timestamp)
    std::unordered_map<uint32_t, int64_t> symbol_timestamps_;

    // Global minimum timestamp (slowest symbol)
    int64_t global_time_{0};

    // Synchronization
    mutable std::mutex mutex_;

public:
    /**
     * @brief Default constructor
     */
    GlobalClock() noexcept = default;

    /**
     * @brief Update timestamp for a specific symbol
     * @param symbol_id Symbol identifier
     * @param timestamp New timestamp in microseconds
     *
     * Updates the symbol's timestamp and recalculates global time.
     * Global time is always the minimum across all tracked symbols.
     *
     * Thread-safe.
     */
    void update_symbol(uint32_t symbol_id, int64_t timestamp) {
        std::lock_guard<std::mutex> lock(mutex_);

        // Update symbol timestamp
        symbol_timestamps_[symbol_id] = timestamp;

        // Recalculate global time (minimum across all symbols)
        recalculate_global_time_locked();
    }

    /**
     * @brief Update multiple symbols at once
     * @param updates Map of symbol_id -> timestamp
     *
     * More efficient than calling update_symbol() multiple times.
     * Thread-safe.
     */
    void update_batch(const std::unordered_map<uint32_t, int64_t>& updates) {
        std::lock_guard<std::mutex> lock(mutex_);

        for (const auto& [symbol_id, timestamp] : updates) {
            symbol_timestamps_[symbol_id] = timestamp;
        }

        recalculate_global_time_locked();
    }

    /**
     * @brief Check if a symbol can advance to a given timestamp
     * @param symbol_id Symbol identifier
     * @param target_timestamp Proposed new timestamp
     * @return true if advancing would not violate PIT constraints
     *
     * A symbol can advance if the target timestamp doesn't exceed
     * the global minimum by more than a tolerance.
     *
     * Thread-safe.
     */
    [[nodiscard]] bool can_advance(uint32_t symbol_id, int64_t target_timestamp) const {
        std::lock_guard<std::mutex> lock(mutex_);

        // If this is the only symbol, can always advance
        if (symbol_timestamps_.size() <= 1) {
            return true;
        }

        // Calculate what global time would be if we exclude this symbol
        int64_t min_time_excluding_self = std::numeric_limits<int64_t>::max();

        for (const auto& [other_id, other_time] : symbol_timestamps_) {
            if (other_id != symbol_id) {
                min_time_excluding_self = std::min(min_time_excluding_self, other_time);
            }
        }

        // Can advance if target doesn't exceed minimum of other symbols
        return target_timestamp <= min_time_excluding_self;
    }

    /**
     * @brief Get current global time
     * @return Minimum timestamp across all symbols, or 0 if no symbols
     *
     * This is the "slowest" symbol's timestamp. All strategies should
     * operate at or before this time to ensure PIT correctness.
     *
     * Thread-safe.
     */
    [[nodiscard]] int64_t current_time() const noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        return global_time_;
    }

    /**
     * @brief Get timestamp for a specific symbol
     * @param symbol_id Symbol identifier
     * @return Symbol's latest timestamp, or 0 if symbol not tracked
     *
     * Thread-safe.
     */
    [[nodiscard]] int64_t get_symbol_time(uint32_t symbol_id) const {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = symbol_timestamps_.find(symbol_id);
        if (it != symbol_timestamps_.end()) {
            return it->second;
        }
        return 0;
    }

    /**
     * @brief Get all symbol timestamps
     * @return Copy of symbol_id -> timestamp map
     *
     * Thread-safe.
     */
    [[nodiscard]] std::unordered_map<uint32_t, int64_t> get_all_timestamps() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return symbol_timestamps_;
    }

    /**
     * @brief Get number of symbols being tracked
     * @return Symbol count
     *
     * Thread-safe.
     */
    [[nodiscard]] size_t symbol_count() const noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        return symbol_timestamps_.size();
    }

    /**
     * @brief Get time lag for a specific symbol
     * @param symbol_id Symbol identifier
     * @return How many microseconds this symbol is ahead of global time
     *
     * A lag of 0 means this symbol is the "slowest" (holding back global time).
     * A positive lag means this symbol is ahead and waiting for others.
     *
     * Thread-safe.
     */
    [[nodiscard]] int64_t get_symbol_lag(uint32_t symbol_id) const {
        std::lock_guard<std::mutex> lock(mutex_);

        auto it = symbol_timestamps_.find(symbol_id);
        if (it != symbol_timestamps_.end()) {
            return it->second - global_time_;
        }
        return 0;
    }

    /**
     * @brief Find the slowest symbol (holding back global time)
     * @return Symbol ID with minimum timestamp, or 0 if no symbols
     *
     * Thread-safe.
     */
    [[nodiscard]] uint32_t get_slowest_symbol() const {
        std::lock_guard<std::mutex> lock(mutex_);

        if (symbol_timestamps_.empty()) {
            return 0;
        }

        uint32_t slowest_id = 0;
        int64_t min_time = std::numeric_limits<int64_t>::max();

        for (const auto& [symbol_id, timestamp] : symbol_timestamps_) {
            if (timestamp < min_time) {
                min_time = timestamp;
                slowest_id = symbol_id;
            }
        }

        return slowest_id;
    }

    /**
     * @brief Remove a symbol from tracking
     * @param symbol_id Symbol identifier
     *
     * After removal, global time is recalculated from remaining symbols.
     * Thread-safe.
     */
    void remove_symbol(uint32_t symbol_id) {
        std::lock_guard<std::mutex> lock(mutex_);

        symbol_timestamps_.erase(symbol_id);
        recalculate_global_time_locked();
    }

    /**
     * @brief Clear all symbols and reset global time
     *
     * Thread-safe.
     */
    void clear() noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        symbol_timestamps_.clear();
        global_time_ = 0;
    }

    /**
     * @brief Reset global time and all symbol timestamps
     * @param initial_time Initial timestamp for all operations
     *
     * Useful when starting a new backtest run.
     * Thread-safe.
     */
    void reset(int64_t initial_time = 0) noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        symbol_timestamps_.clear();
        global_time_ = initial_time;
    }

private:
    /**
     * @brief Recalculate global time from symbol timestamps
     *
     * Must be called with mutex locked.
     */
    void recalculate_global_time_locked() noexcept {
        if (symbol_timestamps_.empty()) {
            global_time_ = 0;
            return;
        }

        int64_t min_time = std::numeric_limits<int64_t>::max();
        for (const auto& [_, timestamp] : symbol_timestamps_) {
            min_time = std::min(min_time, timestamp);
        }

        global_time_ = min_time;
    }
};

/**
 * @brief Point-in-Time (PIT) enforcer for data access
 *
 * Ensures that data queries are clamped to the current global time.
 * Prevents strategies from accessing future data (look-ahead bias).
 *
 * Example:
 * @code
 * GlobalClock clock;
 * clock.update_symbol(1, 1000000);
 * clock.update_symbol(2, 999000);
 *
 * PITEnforcer enforcer(clock);
 *
 * // Request data up to 1001000, but will be clamped to 999000 (global time)
 * int64_t max_time = enforcer.clamp_query_time(1001000);
 * assert(max_time == 999000);
 * @endcode
 */
class PITEnforcer {
private:
    const GlobalClock& clock_;

public:
    /**
     * @brief Constructor
     * @param clock Reference to global clock
     */
    explicit PITEnforcer(const GlobalClock& clock) noexcept
        : clock_(clock) {}

    /**
     * @brief Clamp query timestamp to global time
     * @param query_time Requested timestamp
     * @return Clamped timestamp (min of query_time and global time)
     *
     * This ensures queries cannot access data beyond the global time,
     * preventing look-ahead bias.
     */
    [[nodiscard]] int64_t clamp_query_time(int64_t query_time) const noexcept {
        int64_t global_time = clock_.current_time();
        return std::min(query_time, global_time);
    }

    /**
     * @brief Check if a query time is valid (not in the future)
     * @param query_time Requested timestamp
     * @return true if query_time <= global time
     */
    [[nodiscard]] bool is_valid_query(int64_t query_time) const noexcept {
        return query_time <= clock_.current_time();
    }

    /**
     * @brief Get maximum allowed query time (global time)
     * @return Current global time
     */
    [[nodiscard]] int64_t max_query_time() const noexcept {
        return clock_.current_time();
    }
};

} // namespace hqt
