#include "util/logger.hpp"

#include <atomic>
#include <iostream>
#include <mutex>
#include <utility>

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

void log(const LogLevel level, const std::string& message) {
    if (static_cast<int>(level) < g_log_level.load(std::memory_order_relaxed)) {
        return;
    }

    LogSink sink_copy;
    {
        std::lock_guard<std::mutex> lock(g_sink_mutex);
        sink_copy = g_sink;
    }

    if (sink_copy) {
        sink_copy(level, message);
    }

    if (g_stderr_enabled.load(std::memory_order_relaxed)) {
        std::cerr << "[CPP][" << level_name(level) << "] " << message << '\n';
    }
}

void debug(const std::string& message) {
    log(LogLevel::Debug, message);
}

void info(const std::string& message) {
    log(LogLevel::Info, message);
}

void warning(const std::string& message) {
    log(LogLevel::Warning, message);
}

void error(const std::string& message) {
    log(LogLevel::Error, message);
}

}  // namespace hqt::util
