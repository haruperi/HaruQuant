/**
 * @file logger.cpp
 * @brief Unified engine logger module.
 */

#include "util/logger.hpp"

#include <atomic>
#include <chrono>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <utility>
#if defined(_WIN32)
#include <process.h>
#else
#include <unistd.h>
#endif

namespace hqt::util {
namespace {

std::atomic<int> g_log_level{static_cast<int>(LogLevel::Info)};
std::atomic<bool> g_stderr_enabled{true};
std::mutex g_sink_mutex;
LogSink g_sink;

const char* level_name(const LogLevel level) noexcept {
    switch (level) {
        case LogLevel::Debug: return "DEBUG";
        case LogLevel::Info: return "INFO";
        case LogLevel::Warning: return "WARNING";
        case LogLevel::Error: return "ERROR";
        default: return "INFO";
    }
}

int level_number(const LogLevel level) noexcept {
    return static_cast<int>(level);
}

double now_timestamp_seconds() {
    const auto now = std::chrono::system_clock::now();
    return std::chrono::duration<double>(now.time_since_epoch()).count();
}

std::string now_iso8601_utc() {
    const auto now = std::chrono::system_clock::now();
    const auto tt = std::chrono::system_clock::to_time_t(now);
    const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                        now.time_since_epoch())
                        .count() %
                    1000;
    std::tm tm{};
#if defined(_WIN32)
    gmtime_s(&tm, &tt);
#else
    gmtime_r(&tt, &tm);
#endif
    std::ostringstream oss;
    oss << std::put_time(&tm, "%Y-%m-%dT%H:%M:%S") << '.'
        << std::setw(3) << std::setfill('0') << ms << 'Z';
    return oss.str();
}

int process_id() noexcept {
#if defined(_WIN32)
    return _getpid();
#else
    return getpid();
#endif
}

std::string process_name() {
    return "hqt_cpp";
}

std::uint64_t thread_id() {
    return static_cast<std::uint64_t>(
        std::hash<std::thread::id>{}(std::this_thread::get_id()));
}

std::string thread_name() {
    std::ostringstream oss;
    oss << std::this_thread::get_id();
    return oss.str();
}

std::string file_name_from_path(const std::string& path) {
    return std::filesystem::path(path).filename().string();
}

std::string module_from_path(const std::string& path) {
    return std::filesystem::path(path).stem().string();
}

LogRecord build_record(const LogLevel level, const std::string& message,
                       const std::source_location& location, LogExtra extra) {
    const std::string file_path = location.file_name();
    LogRecord record{};
    record.logger_name = "hqt.cpp";
    record.module = module_from_path(file_path);
    record.file_name = file_name_from_path(file_path);
    record.file_path = file_path;
    record.function = location.function_name();
    record.line = static_cast<int>(location.line());
    record.level_name = level_name(level);
    record.level_no = level_number(level);
    record.message = message;
    record.timestamp = now_timestamp_seconds();
    record.time_repr = now_iso8601_utc();
    record.process_id = process_id();
    record.process_name = process_name();
    record.thread_id = thread_id();
    record.thread_name = thread_name();
    record.extra = std::move(extra);
    return record;
}

}  // namespace

void set_log_level(const LogLevel level) noexcept {
    g_log_level.store(static_cast<int>(level), std::memory_order_relaxed);
}

LogLevel get_log_level() noexcept {
    return static_cast<LogLevel>(g_log_level.load(std::memory_order_relaxed));
}

void set_stderr_logging(const bool enabled) noexcept {
    g_stderr_enabled.store(enabled, std::memory_order_relaxed);
}

bool stderr_logging_enabled() noexcept {
    return g_stderr_enabled.load(std::memory_order_relaxed);
}

void set_log_sink(LogSink sink) {
    std::lock_guard<std::mutex> lock(g_sink_mutex);
    g_sink = std::move(sink);
}

void log(const LogLevel level, const std::string& message,
         const std::source_location& location, LogExtra extra) {
    if (static_cast<int>(level) < g_log_level.load(std::memory_order_relaxed)) {
        return;
    }

    LogRecord record = build_record(level, message, location, std::move(extra));

    LogSink sink_copy;
    {
        std::lock_guard<std::mutex> lock(g_sink_mutex);
        sink_copy = g_sink;
    }

    if (sink_copy) {
        sink_copy(record);
    }

    if (g_stderr_enabled.load(std::memory_order_relaxed)) {
        std::cerr << "[CPP][" << record.level_name << "] "
                  << record.module << ":" << record.line << " "
                  << record.message << '\n';
    }
}

void debug(const std::string& message, const std::source_location& location,
           LogExtra extra) {
    log(LogLevel::Debug, message, location, std::move(extra));
}

void info(const std::string& message, const std::source_location& location,
          LogExtra extra) {
    log(LogLevel::Info, message, location, std::move(extra));
}

void warning(const std::string& message, const std::source_location& location,
             LogExtra extra) {
    log(LogLevel::Warning, message, location, std::move(extra));
}

void error(const std::string& message, const std::source_location& location,
           LogExtra extra) {
    log(LogLevel::Error, message, location, std::move(extra));
}

}  // namespace hqt::util

namespace hqt::engine {

void log_info(const std::string& message) {
    hqt::util::info(message);
}

void log_warning(const std::string& message) {
    hqt::util::warning(message);
}

}  // namespace hqt::engine
