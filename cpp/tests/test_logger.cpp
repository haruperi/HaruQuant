/**
 * @file test_logger.cpp
 * @brief Unit tests for C++ logger behavior.
 */

#include <gtest/gtest.h>
#include "util/logger.hpp"

#include <atomic>
#include <cstdlib>
#include <string>

using namespace hqt::util;
namespace hqt::engine {
void log_info(const std::string& message);
void log_warning(const std::string& message);
}

namespace {
void set_env_flag(const char* key, const char* value) {
#if defined(_WIN32)
    _putenv_s(key, value);
#else
    setenv(key, value, 1);
#endif
}

void clear_env_flag(const char* key) {
#if defined(_WIN32)
    _putenv_s(key, "");
#else
    unsetenv(key);
#endif
}
}  // namespace

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

TEST(LoggerTest, ComponentLevelGetAndClearAll) {
    clear_all_component_log_levels();
    EXPECT_FALSE(get_component_log_level("risk").has_value());

    set_component_log_level("risk", LogLevel::Warning);
    const auto level = get_component_log_level("risk");
    ASSERT_TRUE(level.has_value());
    EXPECT_EQ(*level, LogLevel::Warning);

    clear_all_component_log_levels();
    EXPECT_FALSE(get_component_log_level("risk").has_value());
}

TEST(LoggerTest, ExplicitComponentOverrideApplies) {
    std::atomic<int> sink_calls{0};
    std::string last_message;

    set_stderr_logging(false);
    set_log_level(LogLevel::Info);
    set_component_log_level("orders", LogLevel::Error);
    set_log_sink([&](const LogRecord& record) {
        ++sink_calls;
        last_message = record.message;
    });

    info("should-be-filtered-by-component",
         std::source_location::current(),
         {{"component", "orders"}});
    error("should-pass-by-component",
          std::source_location::current(),
          {{"component", "orders"}});

    EXPECT_EQ(sink_calls.load(), 1);
    EXPECT_EQ(last_message, "should-pass-by-component");

    clear_all_component_log_levels();
    set_log_sink(LogSink{});
}

TEST(LoggerTest, ContextIdsPreservedWhenProvided) {
    std::atomic<int> sink_calls{0};
    std::string correlation_id;
    std::string run_id;
    std::string trace_id;

    set_stderr_logging(false);
    set_log_level(LogLevel::Debug);
    set_log_sink([&](const LogRecord& record) {
        ++sink_calls;
        correlation_id = record.correlation_id;
        run_id = record.run_id;
        trace_id = record.trace_id;
    });

    info("context ids",
         std::source_location::current(),
         {
             {"correlation_id", "cid-1"},
             {"run_id", "run-1"},
             {"trace_id", "trace-1"},
         });

    EXPECT_EQ(sink_calls.load(), 1);
    EXPECT_EQ(correlation_id, "cid-1");
    EXPECT_EQ(run_id, "run-1");
    EXPECT_EQ(trace_id, "trace-1");

    set_log_sink(LogSink{});
}

TEST(LoggerTest, WrapperFunctionsAndStderrToggle) {
    std::atomic<int> sink_calls{0};
    std::string last_message;
    std::string last_level;

    set_stderr_logging(false);
    EXPECT_FALSE(stderr_logging_enabled());
    set_stderr_logging(true);
    EXPECT_TRUE(stderr_logging_enabled());
    set_stderr_logging(false);

    set_log_level(LogLevel::Debug);
    set_log_sink([&](const LogRecord& record) {
        ++sink_calls;
        last_message = record.message;
        last_level = record.level_name;
    });

    debug("debug-wrapper");
    warning("warning-wrapper");
    info("info-wrapper");
    warning("warning-wrapper-2");
    flush_logs();

    EXPECT_GE(sink_calls.load(), 4);
    EXPECT_FALSE(last_message.empty());
    EXPECT_FALSE(last_level.empty());

    set_log_sink(LogSink{});
    set_log_level(LogLevel::Info);
    set_stderr_logging(true);
}

TEST(LoggerTest, WarningAndInvalidLevelPaths) {
    std::atomic<int> sink_calls{0};
    std::string last_level;
    std::string last_message;

    set_stderr_logging(true);
    set_log_level(LogLevel::Warning);
    set_log_sink([&](const LogRecord& record) {
        ++sink_calls;
        last_level = record.level_name;
        last_message = record.message;
    });

    warning("warning-level-path");
    log(static_cast<LogLevel>(999), "invalid-level-default-path");

    EXPECT_GE(sink_calls.load(), 2);
    EXPECT_FALSE(last_level.empty());
    EXPECT_FALSE(last_message.empty());

    hqt::engine::log_info("engine-wrapper-info");
    hqt::engine::log_warning("engine-wrapper-warning");

    set_log_sink(LogSink{});
    set_log_level(LogLevel::Info);
    set_stderr_logging(true);
}

TEST(LoggerTest, ForcedCatchPathsAreHandled) {
    set_stderr_logging(true);
    set_log_level(LogLevel::Info);

    set_env_flag("HQT_LOGGER_TEST_THROW_SET_LEVEL", "1");
    set_log_level(LogLevel::Warning);
    clear_env_flag("HQT_LOGGER_TEST_THROW_SET_LEVEL");
    set_log_level(LogLevel::Info);

    set_env_flag("HQT_LOGGER_TEST_THROW_FLUSH", "1");
    flush_logs();
    clear_env_flag("HQT_LOGGER_TEST_THROW_FLUSH");

    std::atomic<int> sink_calls{0};
    set_log_sink([&](const LogRecord&) { ++sink_calls; });

    set_env_flag("HQT_LOGGER_TEST_THROW_STDERR_LOG", "1");
    info("forced-catch-stderr-path");
    clear_env_flag("HQT_LOGGER_TEST_THROW_STDERR_LOG");

    EXPECT_EQ(sink_calls.load(), 1);

    set_log_sink(LogSink{});
    set_stderr_logging(true);
}
