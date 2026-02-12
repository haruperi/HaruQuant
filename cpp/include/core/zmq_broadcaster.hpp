/**
 * @file zmq_broadcaster.hpp
 * @brief ZMQ broadcaster for real-time event streaming
 *
 * Provides non-blocking PUB socket for broadcasting engine events
 * (ticks, trades, equity updates, orders) to external subscribers.
 * Uses MessagePack for efficient binary serialization.
 */

#pragma once

#include <zmq.hpp>
#include <string>
#include <cstdint>
#include <memory>
#include <stdexcept>

namespace hqt {

/**
 * @brief Exception for ZMQ broadcaster errors
 */
class BroadcasterError : public std::runtime_error {
public:
    explicit BroadcasterError(const std::string& msg) : std::runtime_error(msg) {}
};

/**
 * @brief Message topics for routing
 */
enum class Topic : uint8_t {
    TICK = 0,
    BAR = 1,
    TRADE = 2,
    ORDER = 3,
    EQUITY = 4,
    MARGIN = 5,
    POSITION = 6,
    ACCOUNT = 7
};

/**
 * @brief ZMQ broadcaster for real-time event streaming
 *
 * Uses ZMQ PUB socket in non-blocking mode to broadcast engine events.
 * Messages are serialized with MessagePack and prefixed with topic for filtering.
 *
 * Example:
 * @code
 * ZmqBroadcaster broadcaster("tcp://*:5555");
 * broadcaster.start();
 *
 * // Publish tick
 * broadcaster.publish_tick(symbol_id, timestamp_us, bid, ask);
 *
 * // Publish trade
 * broadcaster.publish_trade(ticket, symbol, volume, price, profit);
 *
 * broadcaster.stop();
 * @endcode
 */
class ZmqBroadcaster {
private:
    std::unique_ptr<zmq::context_t> context_;
    std::unique_ptr<zmq::socket_t> publisher_;
    std::string endpoint_;
    bool running_;
    uint64_t message_count_;
    uint64_t bytes_sent_;

public:
    /**
     * @brief Construct broadcaster with endpoint
     * @param endpoint ZMQ endpoint (e.g., "tcp://*:5555" or "ipc:///tmp/hqt")
     */
    explicit ZmqBroadcaster(const std::string& endpoint = "tcp://*:5555")
        : context_(nullptr),
          publisher_(nullptr),
          endpoint_(endpoint),
          running_(false),
          message_count_(0),
          bytes_sent_(0) {}

    /**
     * @brief Destructor - stops broadcaster if running
     */
    ~ZmqBroadcaster() noexcept {
        if (running_) {
            stop();
        }
    }

    // Disable copy
    ZmqBroadcaster(const ZmqBroadcaster&) = delete;
    ZmqBroadcaster& operator=(const ZmqBroadcaster&) = delete;

    // Enable move
    ZmqBroadcaster(ZmqBroadcaster&&) noexcept = default;
    ZmqBroadcaster& operator=(ZmqBroadcaster&&) noexcept = default;

    /**
     * @brief Start broadcaster (create context and socket)
     * @throws BroadcasterError on failure
     */
    void start() {
        if (running_) return;

        try {
            // Create ZMQ context (1 I/O thread)
            context_ = std::make_unique<zmq::context_t>(1);

            // Create PUB socket
            publisher_ = std::make_unique<zmq::socket_t>(*context_, zmq::socket_type::pub);

            // Set socket options
            int linger = 0;  // Don't wait on close
            publisher_->set(zmq::sockopt::linger, linger);

            int sndhwm = 10000;  // High water mark (queue size)
            publisher_->set(zmq::sockopt::sndhwm, sndhwm);

            // Bind to endpoint
            publisher_->bind(endpoint_);

            running_ = true;
            message_count_ = 0;
            bytes_sent_ = 0;

        } catch (const zmq::error_t& e) {
            throw BroadcasterError("Failed to start broadcaster: " + std::string(e.what()));
        }
    }

    /**
     * @brief Stop broadcaster (close socket and context)
     */
    void stop() noexcept {
        if (!running_) return;

        try {
            if (publisher_) {
                publisher_->close();
                publisher_.reset();
            }
            if (context_) {
                context_->close();
                context_.reset();
            }
            running_ = false;
        } catch (...) {
            // Ignore exceptions during shutdown
        }
    }

    /**
     * @brief Check if broadcaster is running
     */
    bool is_running() const noexcept {
        return running_;
    }

    /**
     * @brief Get message count
     */
    uint64_t message_count() const noexcept {
        return message_count_;
    }

    /**
     * @brief Get bytes sent
     */
    uint64_t bytes_sent() const noexcept {
        return bytes_sent_;
    }

    // ========================================================================
    // Publishing Methods
    // ========================================================================

    /**
     * @brief Publish tick event
     * @param symbol_id Symbol ID
     * @param timestamp_us Timestamp in microseconds
     * @param bid Bid price (fixed-point)
     * @param ask Ask price (fixed-point)
     */
    void publish_tick(uint32_t symbol_id, int64_t timestamp_us, int64_t bid, int64_t ask) {
        if (!running_) return;

        // Format: [topic:1][symbol_id:4][timestamp:8][bid:8][ask:8]
        constexpr size_t size = 1 + 4 + 8 + 8 + 8;
        uint8_t buffer[size];

        buffer[0] = static_cast<uint8_t>(Topic::TICK);
        write_uint32(buffer + 1, symbol_id);
        write_int64(buffer + 5, timestamp_us);
        write_int64(buffer + 13, bid);
        write_int64(buffer + 21, ask);

        send_message(buffer, size);
    }

    /**
     * @brief Publish bar event
     * @param symbol_id Symbol ID
     * @param timeframe Timeframe
     * @param timestamp_us Timestamp
     * @param open Open price
     * @param high High price
     * @param low Low price
     * @param close Close price
     * @param volume Volume
     */
    void publish_bar(uint32_t symbol_id, uint16_t timeframe, int64_t timestamp_us,
                     int64_t open, int64_t high, int64_t low, int64_t close, int64_t volume) {
        if (!running_) return;

        // Format: [topic:1][symbol_id:4][timeframe:2][timestamp:8][OHLC:32][volume:8]
        constexpr size_t size = 1 + 4 + 2 + 8 + 32 + 8;
        uint8_t buffer[size];

        buffer[0] = static_cast<uint8_t>(Topic::BAR);
        write_uint32(buffer + 1, symbol_id);
        write_uint16(buffer + 5, timeframe);
        write_int64(buffer + 7, timestamp_us);
        write_int64(buffer + 15, open);
        write_int64(buffer + 23, high);
        write_int64(buffer + 31, low);
        write_int64(buffer + 39, close);
        write_int64(buffer + 47, volume);

        send_message(buffer, size);
    }

    /**
     * @brief Publish trade event
     * @param ticket Trade ticket
     * @param symbol_id Symbol ID
     * @param timestamp_us Timestamp
     * @param volume Volume
     * @param price Price
     * @param profit Profit (fixed-point)
     */
    void publish_trade(uint64_t ticket, uint32_t symbol_id, int64_t timestamp_us,
                       double volume, double price, int64_t profit) {
        if (!running_) return;

        // Format: [topic:1][ticket:8][symbol_id:4][timestamp:8][volume:8][price:8][profit:8]
        constexpr size_t size = 1 + 8 + 4 + 8 + 8 + 8 + 8;
        uint8_t buffer[size];

        buffer[0] = static_cast<uint8_t>(Topic::TRADE);
        write_uint64(buffer + 1, ticket);
        write_uint32(buffer + 9, symbol_id);
        write_int64(buffer + 13, timestamp_us);
        write_double(buffer + 21, volume);
        write_double(buffer + 29, price);
        write_int64(buffer + 37, profit);

        send_message(buffer, size);
    }

    /**
     * @brief Publish order event
     * @param ticket Order ticket
     * @param symbol_id Symbol ID
     * @param timestamp_us Timestamp
     * @param type Order type
     * @param volume Volume
     * @param price Price
     */
    void publish_order(uint64_t ticket, uint32_t symbol_id, int64_t timestamp_us,
                       uint8_t type, double volume, double price) {
        if (!running_) return;

        // Format: [topic:1][ticket:8][symbol_id:4][timestamp:8][type:1][volume:8][price:8]
        constexpr size_t size = 1 + 8 + 4 + 8 + 1 + 8 + 8;
        uint8_t buffer[size];

        buffer[0] = static_cast<uint8_t>(Topic::ORDER);
        write_uint64(buffer + 1, ticket);
        write_uint32(buffer + 9, symbol_id);
        write_int64(buffer + 13, timestamp_us);
        buffer[21] = type;
        write_double(buffer + 22, volume);
        write_double(buffer + 30, price);

        send_message(buffer, size);
    }

    /**
     * @brief Publish equity update
     * @param timestamp_us Timestamp
     * @param balance Balance (fixed-point)
     * @param equity Equity (fixed-point)
     * @param margin Margin (fixed-point)
     * @param margin_free Free margin (fixed-point)
     */
    void publish_equity(int64_t timestamp_us, int64_t balance, int64_t equity,
                        int64_t margin, int64_t margin_free) {
        if (!running_) return;

        // Format: [topic:1][timestamp:8][balance:8][equity:8][margin:8][margin_free:8]
        constexpr size_t size = 1 + 8 + 8 + 8 + 8 + 8;
        uint8_t buffer[size];

        buffer[0] = static_cast<uint8_t>(Topic::EQUITY);
        write_int64(buffer + 1, timestamp_us);
        write_int64(buffer + 9, balance);
        write_int64(buffer + 17, equity);
        write_int64(buffer + 25, margin);
        write_int64(buffer + 33, margin_free);

        send_message(buffer, size);
    }

    /**
     * @brief Publish account update
     * @param timestamp_us Timestamp
     * @param balance Balance
     * @param equity Equity
     * @param profit Profit
     * @param margin_level Margin level
     */
    void publish_account(int64_t timestamp_us, int64_t balance, int64_t equity,
                         int64_t profit, double margin_level) {
        if (!running_) return;

        // Format: [topic:1][timestamp:8][balance:8][equity:8][profit:8][margin_level:8]
        constexpr size_t size = 1 + 8 + 8 + 8 + 8 + 8;
        uint8_t buffer[size];

        buffer[0] = static_cast<uint8_t>(Topic::ACCOUNT);
        write_int64(buffer + 1, timestamp_us);
        write_int64(buffer + 9, balance);
        write_int64(buffer + 17, equity);
        write_int64(buffer + 25, profit);
        write_double(buffer + 33, margin_level);

        send_message(buffer, size);
    }

private:
    /**
     * @brief Send message via ZMQ (non-blocking)
     */
    void send_message(const uint8_t* data, size_t size) {
        if (!running_ || !publisher_) return;

        try {
            zmq::message_t message(data, size);
            publisher_->send(message, zmq::send_flags::dontwait);

            message_count_++;
            bytes_sent_ += size;
        } catch (const zmq::error_t&) {
            // Ignore send errors (non-blocking, queue full)
        }
    }

    // ========================================================================
    // Binary serialization helpers
    // ========================================================================

    static void write_uint16(uint8_t* dest, uint16_t value) {
        dest[0] = static_cast<uint8_t>(value & 0xFF);
        dest[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
    }

    static void write_uint32(uint8_t* dest, uint32_t value) {
        dest[0] = static_cast<uint8_t>(value & 0xFF);
        dest[1] = static_cast<uint8_t>((value >> 8) & 0xFF);
        dest[2] = static_cast<uint8_t>((value >> 16) & 0xFF);
        dest[3] = static_cast<uint8_t>((value >> 24) & 0xFF);
    }

    static void write_uint64(uint8_t* dest, uint64_t value) {
        for (int i = 0; i < 8; ++i) {
            dest[i] = static_cast<uint8_t>((value >> (i * 8)) & 0xFF);
        }
    }

    static void write_int64(uint8_t* dest, int64_t value) {
        write_uint64(dest, static_cast<uint64_t>(value));
    }

    static void write_double(uint8_t* dest, double value) {
        union {
            double d;
            uint64_t u;
        } converter;
        converter.d = value;
        write_uint64(dest, converter.u);
    }
};

} // namespace hqt
