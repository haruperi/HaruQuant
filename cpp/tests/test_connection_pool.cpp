/**
FILE: tests\test_connection_pool.cpp

PURPOSE:
Defines test_connection_pool.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in test_connection_pool.cpp.
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
#include <gtest/gtest.h>
#include "util/connection_pool.hpp"

#include <chrono>

using hqt::util::ConnectionPool;
using hqt::util::ConnectionPoolConfig;

TEST(ConnectionPoolTest, AcquireUpToCapacityThenTimesOut) {
    ConnectionPool pool(ConnectionPoolConfig{
        .pool_size = 1,
        .max_overflow = 1,
        .acquire_timeout = std::chrono::milliseconds(5),
    });

    auto lease1 = pool.acquire();
    auto lease2 = pool.acquire();
    auto lease3 = pool.acquire();

    ASSERT_TRUE(lease1.has_value());
    ASSERT_TRUE(lease2.has_value());
    EXPECT_FALSE(lease3.has_value());
    EXPECT_EQ(pool.in_use(), 2U);
}

TEST(ConnectionPoolTest, OverflowLeaseFlagIsSet) {
    ConnectionPool pool(ConnectionPoolConfig{
        .pool_size = 1,
        .max_overflow = 1,
        .acquire_timeout = std::chrono::milliseconds(20),
    });

    auto lease1 = pool.acquire();
    auto lease2 = pool.acquire();

    ASSERT_TRUE(lease1.has_value());
    ASSERT_TRUE(lease2.has_value());
    EXPECT_FALSE(lease1->is_overflow());
    EXPECT_TRUE(lease2->is_overflow());
    EXPECT_EQ(pool.base_in_use(), 1U);
    EXPECT_EQ(pool.overflow_in_use(), 1U);
}

TEST(ConnectionPoolTest, LeaseReleaseUnblocksNextAcquire) {
    ConnectionPool pool(ConnectionPoolConfig{
        .pool_size = 1,
        .max_overflow = 0,
        .acquire_timeout = std::chrono::milliseconds(20),
    });

    {
        auto lease1 = pool.acquire();
        ASSERT_TRUE(lease1.has_value());
        EXPECT_EQ(pool.in_use(), 1U);
    }

    auto lease2 = pool.acquire();
    ASSERT_TRUE(lease2.has_value());
    EXPECT_EQ(pool.in_use(), 1U);
}


