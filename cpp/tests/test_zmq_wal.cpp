/**
 * @file test_zmq_wal.cpp
 * @brief Tests for ZMQ broadcaster and Write-Ahead Log
 */

#include <gtest/gtest.h>
#include "engine/zmq_broadcaster.hpp"
#include "engine/write_ahead_log.hpp"
#include <thread>
#include <chrono>

using namespace hqt;

// ============================================================================
// ZMQ Broadcaster Tests
// ============================================================================

TEST(ZmqBroadcaster, Construction) {
    ZmqBroadcaster broadcaster("tcp://*:5556");
    EXPECT_FALSE(broadcaster.is_running());
    EXPECT_EQ(broadcaster.message_count(), 0);
    EXPECT_EQ(broadcaster.bytes_sent(), 0);
}

TEST(ZmqBroadcaster, StartStop) {
    ZmqBroadcaster broadcaster("tcp://*:5557");

    // Start
    EXPECT_NO_THROW(broadcaster.start());
    EXPECT_TRUE(broadcaster.is_running());

    // Stop
    broadcaster.stop();
    EXPECT_FALSE(broadcaster.is_running());
}

TEST(ZmqBroadcaster, PublishTick) {
    ZmqBroadcaster broadcaster("tcp://*:5558");
    broadcaster.start();

    // Publish tick
    broadcaster.publish_tick(1, 1000000LL, 1100000LL, 1100015LL);

    EXPECT_EQ(broadcaster.message_count(), 1);
    EXPECT_GT(broadcaster.bytes_sent(), 0);

    broadcaster.stop();
}

TEST(ZmqBroadcaster, PublishBar) {
    ZmqBroadcaster broadcaster("tcp://*:5559");
    broadcaster.start();

    // Publish bar
    broadcaster.publish_bar(1, 1, 1000000LL, 1100000LL, 1100100LL, 1099900LL, 1100050LL, 1000LL);

    EXPECT_EQ(broadcaster.message_count(), 1);
    EXPECT_GT(broadcaster.bytes_sent(), 0);

    broadcaster.stop();
}

TEST(ZmqBroadcaster, PublishTrade) {
    ZmqBroadcaster broadcaster("tcp://*:5560");
    broadcaster.start();

    // Publish trade
    broadcaster.publish_trade(12345, 1, 1000000LL, 0.1, 1.10000, 95000000LL);

    EXPECT_EQ(broadcaster.message_count(), 1);
    EXPECT_GT(broadcaster.bytes_sent(), 0);

    broadcaster.stop();
}

TEST(ZmqBroadcaster, PublishOrder) {
    ZmqBroadcaster broadcaster("tcp://*:5561");
    broadcaster.start();

    // Publish order
    broadcaster.publish_order(12345, 1, 1000000LL, 0, 0.1, 1.10000);

    EXPECT_EQ(broadcaster.message_count(), 1);
    EXPECT_GT(broadcaster.bytes_sent(), 0);

    broadcaster.stop();
}

TEST(ZmqBroadcaster, PublishEquity) {
    ZmqBroadcaster broadcaster("tcp://*:5562");
    broadcaster.start();

    // Publish equity
    broadcaster.publish_equity(1000000LL, 10000000000LL, 10095000000LL, 100000000LL, 9995000000LL);

    EXPECT_EQ(broadcaster.message_count(), 1);
    EXPECT_GT(broadcaster.bytes_sent(), 0);

    broadcaster.stop();
}

TEST(ZmqBroadcaster, PublishAccount) {
    ZmqBroadcaster broadcaster("tcp://*:5563");
    broadcaster.start();

    // Publish account
    broadcaster.publish_account(1000000LL, 10000000000LL, 10095000000LL, 95000000LL, 1009.5);

    EXPECT_EQ(broadcaster.message_count(), 1);
    EXPECT_GT(broadcaster.bytes_sent(), 0);

    broadcaster.stop();
}

TEST(ZmqBroadcaster, MultipleMessages) {
    ZmqBroadcaster broadcaster("tcp://*:5564");
    broadcaster.start();

    // Publish multiple messages
    for (int i = 0; i < 100; ++i) {
        broadcaster.publish_tick(1, i * 1000000LL, 1100000LL + i, 1100015LL + i);
    }

    EXPECT_EQ(broadcaster.message_count(), 100);
    EXPECT_GT(broadcaster.bytes_sent(), 0);

    broadcaster.stop();
}

TEST(ZmqBroadcaster, NonBlockingPublish) {
    ZmqBroadcaster broadcaster("tcp://*:5565");
    broadcaster.start();

    // Publish rapidly without blocking
    auto start = std::chrono::high_resolution_clock::now();

    for (int i = 0; i < 1000; ++i) {
        broadcaster.publish_tick(1, i * 1000LL, 1100000LL, 1100015LL);
    }

    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    // Should complete quickly (non-blocking)
    EXPECT_LT(duration.count(), 100);  // Less than 100ms

    broadcaster.stop();
}

// ============================================================================
// Write-Ahead Log Tests
// ============================================================================

TEST(WriteAheadLog, Construction) {
    WriteAheadLog wal("test_wal.dat");
    EXPECT_FALSE(wal.is_wal_open());
    EXPECT_EQ(wal.entry_count(), 0);
    EXPECT_EQ(wal.bytes_written(), 0);
}

TEST(WriteAheadLog, OpenClose) {
    WriteAheadLog wal("test_wal_open.dat");

    // Open
    EXPECT_NO_THROW(wal.open(true));  // Truncate
    EXPECT_TRUE(wal.is_wal_open());

    // Close
    wal.close();
    EXPECT_FALSE(wal.is_wal_open());
}

TEST(WriteAheadLog, AppendEntry) {
    WriteAheadLog wal("test_wal_append.dat");
    wal.open(true);

    // Append entry
    uint8_t data[] = {1, 2, 3, 4, 5};
    EXPECT_NO_THROW(wal.append(WALEntryType::POSITION_OPEN, data, sizeof(data)));

    EXPECT_EQ(wal.entry_count(), 1);
    EXPECT_GT(wal.bytes_written(), 0);

    wal.close();
}

TEST(WriteAheadLog, ReadAll) {
    WriteAheadLog wal("test_wal_read.dat");
    wal.open(true);

    // Write entries
    uint8_t data1[] = {1, 2, 3};
    uint8_t data2[] = {4, 5, 6, 7};

    wal.append(WALEntryType::POSITION_OPEN, data1, sizeof(data1));
    wal.append(WALEntryType::POSITION_CLOSE, data2, sizeof(data2));

    // Read all
    auto entries = wal.read_all();

    EXPECT_EQ(entries.size(), 2);
    EXPECT_EQ(entries[0].first, WALEntryType::POSITION_OPEN);
    EXPECT_EQ(entries[0].second.size(), 3);
    EXPECT_EQ(entries[1].first, WALEntryType::POSITION_CLOSE);
    EXPECT_EQ(entries[1].second.size(), 4);

    wal.close();
}

TEST(WriteAheadLog, CRC32Verification) {
    WriteAheadLog wal("test_wal_crc.dat");
    wal.open(true);

    // Write entry
    uint8_t data[] = {0xDE, 0xAD, 0xBE, 0xEF};
    wal.append(WALEntryType::BALANCE_CHANGE, data, sizeof(data));

    // Read and verify CRC
    auto entries = wal.read_all();

    EXPECT_EQ(entries.size(), 1);
    EXPECT_EQ(entries[0].second[0], 0xDE);
    EXPECT_EQ(entries[0].second[1], 0xAD);
    EXPECT_EQ(entries[0].second[2], 0xBE);
    EXPECT_EQ(entries[0].second[3], 0xEF);

    wal.close();
}

TEST(WriteAheadLog, Checkpoint) {
    WriteAheadLog wal("test_wal_checkpoint.dat");
    wal.open(true);

    // Write entries before checkpoint
    uint8_t data1[] = {1, 2, 3};
    wal.append(WALEntryType::POSITION_OPEN, data1, sizeof(data1));
    wal.append(WALEntryType::POSITION_CLOSE, data1, sizeof(data1));

    // Mark checkpoint
    wal.mark_checkpoint();

    // Write entries after checkpoint
    uint8_t data2[] = {4, 5, 6};
    wal.append(WALEntryType::POSITION_MODIFY, data2, sizeof(data2));

    // Read uncommitted (after checkpoint)
    auto uncommitted = wal.read_uncommitted();

    // Should only get entries after checkpoint
    EXPECT_EQ(uncommitted.size(), 1);
    EXPECT_EQ(uncommitted[0].first, WALEntryType::POSITION_MODIFY);

    wal.close();
}

TEST(WriteAheadLog, MultipleCheckpoints) {
    WriteAheadLog wal("test_wal_multi_checkpoint.dat");
    wal.open(true);

    // First batch
    uint8_t data1[] = {1};
    wal.append(WALEntryType::POSITION_OPEN, data1, 1);
    wal.mark_checkpoint();

    // Second batch
    uint8_t data2[] = {2};
    wal.append(WALEntryType::POSITION_CLOSE, data2, 1);
    wal.mark_checkpoint();

    // Third batch
    uint8_t data3[] = {3};
    wal.append(WALEntryType::POSITION_MODIFY, data3, 1);

    // Read uncommitted (after last checkpoint)
    auto uncommitted = wal.read_uncommitted();

    // Should only get entry after last checkpoint
    EXPECT_EQ(uncommitted.size(), 1);
    EXPECT_EQ(uncommitted[0].first, WALEntryType::POSITION_MODIFY);

    wal.close();
}

TEST(WriteAheadLog, Clear) {
    WriteAheadLog wal("test_wal_clear.dat");
    wal.open(true);

    // Write some entries
    uint8_t data[] = {1, 2, 3};
    wal.append(WALEntryType::POSITION_OPEN, data, sizeof(data));
    wal.append(WALEntryType::POSITION_CLOSE, data, sizeof(data));

    EXPECT_EQ(wal.entry_count(), 2);

    // Clear
    wal.clear();

    // Should be empty
    auto entries = wal.read_all();
    EXPECT_EQ(entries.size(), 0);

    wal.close();
}

TEST(WriteAheadLog, LargeEntry) {
    WriteAheadLog wal("test_wal_large.dat");
    wal.open(true);

    // Create large entry (10KB)
    std::vector<uint8_t> large_data(10240);
    for (size_t i = 0; i < large_data.size(); ++i) {
        large_data[i] = static_cast<uint8_t>(i & 0xFF);
    }

    // Write and read
    wal.append(WALEntryType::CHECKPOINT, large_data.data(), large_data.size());

    auto entries = wal.read_all();
    EXPECT_EQ(entries.size(), 1);
    EXPECT_EQ(entries[0].second.size(), 10240);

    // Verify data integrity
    for (size_t i = 0; i < entries[0].second.size(); ++i) {
        EXPECT_EQ(entries[0].second[i], static_cast<uint8_t>(i & 0xFF));
    }

    wal.close();
}

TEST(WriteAheadLog, EmptyEntry) {
    WriteAheadLog wal("test_wal_empty.dat");
    wal.open(true);

    // Write entry with no data
    wal.append(WALEntryType::CHECKPOINT, nullptr, 0);

    auto entries = wal.read_all();
    EXPECT_EQ(entries.size(), 1);
    EXPECT_EQ(entries[0].second.size(), 0);

    wal.close();
}

TEST(WriteAheadLog, Persistence) {
    const std::string filename = "test_wal_persist.dat";

    // Write entries
    {
        WriteAheadLog wal(filename);
        wal.open(true);

        uint8_t data[] = {0xCA, 0xFE, 0xBA, 0xBE};
        wal.append(WALEntryType::POSITION_OPEN, data, sizeof(data));

        wal.close();
    }

    // Read entries in new instance
    {
        WriteAheadLog wal(filename);
        wal.open(false);  // Don't truncate

        auto entries = wal.read_all();
        EXPECT_EQ(entries.size(), 1);
        EXPECT_EQ(entries[0].second[0], 0xCA);
        EXPECT_EQ(entries[0].second[1], 0xFE);
        EXPECT_EQ(entries[0].second[2], 0xBA);
        EXPECT_EQ(entries[0].second[3], 0xBE);

        wal.close();
    }
}

// Entry point is provided by GTest::gtest_main
