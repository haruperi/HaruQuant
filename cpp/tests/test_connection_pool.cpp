/**
 * @file test_connection_pool.cpp
 * @brief Unit tests for connection pool primitive.
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

