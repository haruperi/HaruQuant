/**
FILE: include\engine\event_loop.hpp

PURPOSE:
Defines event_loop.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in event_loop.hpp.
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
#pragma once

#include "event.hpp"
#include <queue>
#include <vector>
#include <functional>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <stdexcept>

namespace hqt {

/**
 * @brief Event loop with priority queue and lifecycle controls
 *
 * Processes events in strict chronological order. Events are stored in a
 * min-heap priority queue ordered by timestamp. Supports interactive debugging
 * through pause/resume/step operations.
 *
 * Thread-safety: Multiple threads can push events concurrently, but only
 * one thread should call run().
 *
 * Example:
 * @code
 * EventLoop loop;
 * loop.push(Event::tick(1000000, 1));
 * loop.push(Event::bar_close(2000000, 1, static_cast<uint16_t>(Timeframe::M1)));
 *
 * loop.run([](const Event& e) {
 *     if (e.type == EventType::TICK) {
 *         process_tick(e);
 *     }
 * });
 * @endcode
 */
class EventLoop {
public:
    /**
     * @brief Event handler callback signature
     *
     * Called for each event in chronological order.
     * Handler should not throw exceptions.
     */
    using EventHandler = std::function<void(const Event&)>;

private:
    // Priority queue (min-heap) - Events processed in timestamp order
    // Using EventComparator for min-heap (earliest timestamp first)
    std::priority_queue<Event, std::vector<Event>, EventComparator> queue_;

    // Lifecycle control flags
    std::atomic<bool> running_{false};
    std::atomic<bool> paused_{false};
    std::atomic<bool> stopped_{false};

    // Synchronization for pause/resume
    mutable std::mutex mutex_;
    std::condition_variable cv_;

    // Statistics
    std::atomic<uint64_t> events_processed_{0};
    std::atomic<int64_t> current_timestamp_{0};

public:
    /**
     * @brief Default constructor
     */
    EventLoop() noexcept = default;

    /**
     * @brief Destructor - stops the loop if running
     */
    ~EventLoop() noexcept {
        stop();
    }

    // Non-copyable, non-movable (contains atomics and mutex)
    EventLoop(const EventLoop&) = delete;
    EventLoop& operator=(const EventLoop&) = delete;
    EventLoop(EventLoop&&) = delete;
    EventLoop& operator=(EventLoop&&) = delete;

    /**
     * @brief Push an event into the queue
     * @param event Event to add
     *
     * Thread-safe. Can be called while loop is running.
     */
    void push(Event event) {
        std::lock_guard<std::mutex> lock(mutex_);
        queue_.push(std::move(event));
        cv_.notify_one();  // Wake up run() if it's waiting
    }

    /**
     * @brief Push multiple events at once
     * @param events Vector of events to add
     *
     * More efficient than calling push() multiple times.
     */
    void push_batch(const std::vector<Event>& events) {
        std::lock_guard<std::mutex> lock(mutex_);
        for (const auto& event : events) {
            queue_.push(event);
        }
        cv_.notify_one();
    }

    /**
     * @brief Run the event loop until completion or stop
     * @param handler Callback invoked for each event
     * @throws std::runtime_error if already running
     *
     * Processes all events in chronological order. Blocks until:
     * - Queue is empty
     * - stop() is called
     *
     * If paused, waits until resume() is called.
     */
    void run(EventHandler handler) {
        if (running_.exchange(true)) {
            throw std::runtime_error("EventLoop is already running");
        }

        stopped_ = false;
        events_processed_ = 0;

        while (true) {
            // Check if paused
            {
                std::unique_lock<std::mutex> lock(mutex_);
                cv_.wait(lock, [this] { return !paused_ || stopped_; });
            }

            // Check if stopped
            if (stopped_) {
                break;
            }

            // Get next event
            Event event;
            {
                std::lock_guard<std::mutex> lock(mutex_);
                if (queue_.empty()) {
                    break;  // No more events
                }
                event = queue_.top();
                queue_.pop();
            }

            // Update current timestamp
            current_timestamp_ = event.timestamp_us;

            // Process event
            try {
                handler(event);
            } catch (const std::exception&) {
                // Handler should not throw, but handle gracefully if it does
                // In production, log error and continue
                // For now, rethrow to help debugging
                running_ = false;
                throw;
            }

            ++events_processed_;
        }

        running_ = false;
    }

    /**
     * @brief Pause event processing
     *
     * The loop will finish processing the current event, then wait
     * until resume() is called. Thread-safe.
     */
    void pause() noexcept {
        paused_ = true;
    }

    /**
     * @brief Resume event processing after pause
     *
     * Thread-safe.
     */
    void resume() noexcept {
        paused_ = false;
        cv_.notify_one();
    }

    /**
     * @brief Stop the event loop
     *
     * Causes run() to exit after processing the current event.
     * Remaining events stay in the queue. Thread-safe.
     */
    void stop() noexcept {
        stopped_ = true;
        cv_.notify_all();
    }

    /**
     * @brief Process exactly N events, then pause
     * @param n Number of events to process
     * @param handler Event handler callback
     * @throws std::runtime_error if already running
     *
     * Useful for step-by-step debugging. Processes exactly N events
     * in chronological order, then automatically pauses.
     *
     * Example:
     * @code
     * loop.step(1, handler);  // Process one event
     * // Inspect state
     * loop.step(10, handler); // Process 10 more events
     * @endcode
     */
    void step(size_t n, EventHandler handler) {
        if (running_.exchange(true)) {
            throw std::runtime_error("EventLoop is already running");
        }

        stopped_ = false;
        events_processed_ = 0;

        for (size_t i = 0; i < n; ++i) {
            // Check if stopped
            if (stopped_) {
                break;
            }

            // Get next event
            Event event;
            {
                std::lock_guard<std::mutex> lock(mutex_);
                if (queue_.empty()) {
                    break;  // No more events
                }
                event = queue_.top();
                queue_.pop();
            }

            // Update current timestamp
            current_timestamp_ = event.timestamp_us;

            // Process event
            try {
                handler(event);
            } catch (const std::exception&) {
                running_ = false;
                throw;
            }

            ++events_processed_;
        }

        running_ = false;
    }

    /**
     * @brief Get number of events currently in queue
     * @return Queue size
     *
     * Thread-safe but value may change immediately after return.
     */
    [[nodiscard]] size_t size() const noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.size();
    }

    /**
     * @brief Check if queue is empty
     * @return true if no events in queue
     *
     * Thread-safe but value may change immediately after return.
     */
    [[nodiscard]] bool empty() const noexcept {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.empty();
    }

    /**
     * @brief Check if loop is currently running
     * @return true if run() or step() is executing
     */
    [[nodiscard]] bool is_running() const noexcept {
        return running_;
    }

    /**
     * @brief Check if loop is paused
     * @return true if paused
     */
    [[nodiscard]] bool is_paused() const noexcept {
        return paused_;
    }

    /**
     * @brief Check if loop has been stopped
     * @return true if stop() was called
     */
    [[nodiscard]] bool is_stopped() const noexcept {
        return stopped_;
    }

    /**
     * @brief Get total number of events processed since last run/step
     * @return Event count
     */
    [[nodiscard]] uint64_t events_processed() const noexcept {
        return events_processed_;
    }

    /**
     * @brief Get current simulation timestamp (most recent event)
     * @return Timestamp in microseconds, or 0 if no events processed yet
     */
    [[nodiscard]] int64_t current_timestamp() const noexcept {
        return current_timestamp_;
    }

    /**
     * @brief Clear all events from queue
     *
     * Should only be called when loop is not running.
     * Not thread-safe with run().
     */
    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        // Clear by replacing with empty queue
        std::priority_queue<Event, std::vector<Event>, EventComparator> empty;
        std::swap(queue_, empty);
        events_processed_ = 0;
        current_timestamp_ = 0;
    }
};

} // namespace hqt

