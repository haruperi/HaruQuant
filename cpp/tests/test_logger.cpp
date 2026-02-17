/**
 * @file test_logger.cpp
 * @brief Unit tests for C++ logger behavior.
 */

#include <gtest/gtest.h>
#include "util/logger.hpp"

#include <atomic>
#include <string>

using namespace hqt::util;

TEST(LoggerTest, SinkReceivesStructuredRecord) {
    std::atomic<int> sink_calls{0};
    std::string last_message;
    std::string last_level;
    std::string correlation_id;
    std::string run_id;
    std::string trace_id;

    set_stderr_logging(false);
    set_log_level(LogLevel::Debug);
    set_log_sink([&](const LogRecord& record) {
        ++sink_calls;
        last_message = record.message;
        last_level = record.level_name;
        correlation_id = record.correlation_id;
        run_id = record.run_id;
        trace_id = record.trace_id;
    });

    info("logger sink test message");

    EXPECT_EQ(sink_calls.load(), 1);
    EXPECT_EQ(last_message, "logger sink test message");
    EXPECT_EQ(last_level, "INFO");
    EXPECT_EQ(correlation_id, "");
    EXPECT_EQ(run_id, "");
    EXPECT_EQ(trace_id, "");

    set_log_sink(LogSink{});
}

TEST(LoggerTest, LevelFilteringWorks) {
    std::atomic<int> sink_calls{0};

    set_stderr_logging(false);
    set_log_level(LogLevel::Error);
    set_log_sink([&](const LogRecord&) {
        ++sink_calls;
    });

    info("should be filtered");
    error("should pass");

    EXPECT_EQ(sink_calls.load(), 1);

    set_log_sink(LogSink{});
    set_log_level(LogLevel::Info);
}

TEST(LoggerTest, CriticalLevelIsEmittedAndFiltersLowerLevels) {
    std::atomic<int> sink_calls{0};
    std::string last_level;

    set_stderr_logging(false);
    set_log_level(LogLevel::Critical);
    set_log_sink([&](const LogRecord& record) {
        ++sink_calls;
        last_level = record.level_name;
    });

    error("should be filtered");
    critical("critical should pass");

    EXPECT_EQ(sink_calls.load(), 1);
    EXPECT_EQ(last_level, "CRITICAL");

    set_log_sink(LogSink{});
    set_log_level(LogLevel::Info);
}

TEST(LoggerTest, ComponentLevelOverrideFiltersAtRuntime) {
    std::atomic<int> sink_calls{0};
    std::string last_message;

    set_stderr_logging(false);
    set_log_level(LogLevel::Debug);
    set_component_log_level("test_logger", LogLevel::Error);
    set_log_sink([&](const LogRecord& record) {
        ++sink_calls;
        last_message = record.message;
    });

    info("component-filtered");
    error("component-error-pass");

    EXPECT_EQ(sink_calls.load(), 1);
    EXPECT_EQ(last_message, "component-error-pass");

    clear_component_log_level("test_logger");
    set_log_sink(LogSink{});
    set_log_level(LogLevel::Info);
}

TEST(LoggerTest, RedactsSensitiveMessageAndExtraFields) {
    std::atomic<int> sink_calls{0};
    std::string last_message;
    std::string redacted_password;
    std::string safe_value;

    set_stderr_logging(false);
    set_log_level(LogLevel::Debug);
    set_log_sink([&](const LogRecord& record) {
        ++sink_calls;
        last_message = record.message;
        redacted_password = record.extra.at("password");
        safe_value = record.extra.at("safe");
    });

    info("auth failed password=supersecret token=abcd",
         std::source_location::current(),
         {{"password", "my-password"}, {"safe", "ok"}});

    EXPECT_EQ(sink_calls.load(), 1);
    EXPECT_EQ(last_message.find("supersecret"), std::string::npos);
    EXPECT_EQ(last_message.find("abcd"), std::string::npos);
    EXPECT_NE(last_message.find("***REDACTED***"), std::string::npos);
    EXPECT_EQ(redacted_password, "***REDACTED***");
    EXPECT_EQ(safe_value, "ok");

    set_log_sink(LogSink{});
    set_log_level(LogLevel::Info);
}
