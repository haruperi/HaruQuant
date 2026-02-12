/**
 * @file event.hpp
 * @brief Event structure for the event-driven engine
 *
 * The event loop processes events in chronological order using a priority queue.
 * All events are timestamped and ordered by timestamp_us.
 */

#pragma once

#include <cstdint>
#include <compare>

namespace hqt {

/**
 * @brief Event type enumeration
 *
 * Different event types trigger different handlers in the event loop.
 */
enum class EventType : uint8_t {
    TICK        = 0,  ///< New tick (price quote) received
    BAR_CLOSE   = 1,  ///< Bar completed (for bar-based strategies)
    ORDER_TRIGGER = 2,  ///< Pending order trigger check
    TIMER       = 3,  ///< Timer event (for periodic callbacks)
    CUSTOM      = 4   ///< Custom user-defined event
};

/**
 * @brief Event data union
 *
 * Stores event-specific data without heap allocation.
 * The actual type is determined by the EventType.
 */
union EventData {
    struct {
        uint32_t symbol_id;  ///< Symbol ID for tick/bar events
        uint32_t reserved;
    } tick_data;

    struct {
        uint32_t symbol_id;  ///< Symbol ID
        uint16_t timeframe;  ///< Timeframe (cast to Timeframe enum)
        uint16_t reserved;
    } bar_data;

    struct {
        uint64_t order_ticket;  ///< Order ticket to check
    } order_data;

    struct {
        uint32_t timer_id;   ///< Timer identifier
        uint32_t reserved;
    } timer_data;

    uint64_t raw_data;  ///< Raw 64-bit data for custom events

    constexpr EventData() noexcept : raw_data(0) {}
};

/**
 * @brief Event structure for priority queue
 *
 * Events are ordered by timestamp for chronological processing.
 * Uses C++20 three-way comparison for efficient ordering.
 */
struct Event {
    int64_t timestamp_us;  ///< Event timestamp (microseconds since epoch)
    EventType type;        ///< Event type
    EventData data;        ///< Event-specific data

    /**
     * @brief Default constructor
     */
    constexpr Event() noexcept
        : timestamp_us(0)
        , type(EventType::CUSTOM)
        , data()
    {}

    /**
     * @brief Construct event with timestamp and type
     */
    constexpr Event(int64_t ts, EventType t) noexcept
        : timestamp_us(ts)
        , type(t)
        , data()
    {}

    /**
     * @brief Construct tick event
     */
    [[nodiscard]] static constexpr Event tick(int64_t ts, uint32_t symbol_id) noexcept {
        Event e(ts, EventType::TICK);
        e.data.tick_data.symbol_id = symbol_id;
        return e;
    }

    /**
     * @brief Construct bar close event
     */
    [[nodiscard]] static constexpr Event bar_close(int64_t ts, uint32_t symbol_id, uint16_t timeframe) noexcept {
        Event e(ts, EventType::BAR_CLOSE);
        e.data.bar_data.symbol_id = symbol_id;
        e.data.bar_data.timeframe = timeframe;
        return e;
    }

    /**
     * @brief Construct order trigger check event
     */
    [[nodiscard]] static constexpr Event order_trigger(int64_t ts, uint64_t order_ticket) noexcept {
        Event e(ts, EventType::ORDER_TRIGGER);
        e.data.order_data.order_ticket = order_ticket;
        return e;
    }

    /**
     * @brief Construct timer event
     */
    [[nodiscard]] static constexpr Event timer(int64_t ts, uint32_t timer_id) noexcept {
        Event e(ts, EventType::TIMER);
        e.data.timer_data.timer_id = timer_id;
        return e;
    }

    /**
     * @brief Three-way comparison operator for priority queue ordering
     *
     * Events are ordered by timestamp (earliest first).
     * For min-heap priority_queue, we need GREATER comparison.
     */
    [[nodiscard]] constexpr auto operator<=>(const Event& other) const noexcept {
        // Compare timestamps (earlier events have higher priority)
        // For std::priority_queue, the "top" is the largest element
        // So we reverse the comparison to get earliest events on top
        return other.timestamp_us <=> timestamp_us;
    }

    /**
     * @brief Equality comparison
     */
    [[nodiscard]] constexpr bool operator==(const Event& other) const noexcept {
        return timestamp_us == other.timestamp_us &&
               type == other.type &&
               data.raw_data == other.data.raw_data;
    }
};

/**
 * @brief Comparator for priority queue (min-heap by timestamp)
 *
 * This gives us earliest events first.
 */
struct EventComparator {
    [[nodiscard]] constexpr bool operator()(const Event& a, const Event& b) const noexcept {
        // Return true if a should come AFTER b (i.e., a has later timestamp)
        // This creates a min-heap where earliest events are at the top
        return a.timestamp_us > b.timestamp_us;
    }
};

} // namespace hqt
