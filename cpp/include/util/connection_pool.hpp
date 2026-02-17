/**
 * @file connection_pool.hpp
 * @brief Configurable connection-pool concurrency primitive.
 */

#pragma once

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <mutex>
#include <optional>

namespace hqt::util {

struct ConnectionPoolConfig {
    std::size_t pool_size{4};
    std::size_t max_overflow{2};
    std::chrono::milliseconds acquire_timeout{std::chrono::milliseconds(1000)};
};

class ConnectionPool {
public:
    class Lease {
    public:
        Lease() = default;
        Lease(const Lease&) = delete;
        Lease& operator=(const Lease&) = delete;
        Lease(Lease&& other) noexcept;
        Lease& operator=(Lease&& other) noexcept;
        ~Lease();

        [[nodiscard]] bool valid() const noexcept;
        [[nodiscard]] bool is_overflow() const noexcept;

    private:
        friend class ConnectionPool;
        Lease(ConnectionPool* owner, bool overflow) noexcept;
        void reset() noexcept;

        ConnectionPool* owner_{nullptr};
        bool overflow_{false};
    };

    explicit ConnectionPool(ConnectionPoolConfig config = {});

    [[nodiscard]] std::optional<Lease> acquire();
    [[nodiscard]] std::size_t in_use() const;
    [[nodiscard]] std::size_t base_in_use() const;
    [[nodiscard]] std::size_t overflow_in_use() const;
    [[nodiscard]] std::size_t capacity() const;
    [[nodiscard]] ConnectionPoolConfig config() const;

private:
    friend class Lease;
    void release(bool overflow);

    ConnectionPoolConfig config_;
    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::size_t base_in_use_{0};
    std::size_t overflow_in_use_{0};
};

}  // namespace hqt::util

