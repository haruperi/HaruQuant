/**
FILE: include\util\connection_pool.hpp

PURPOSE:
Defines connection_pool.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in connection_pool.hpp.
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


