/**
FILE: src\engine\logger.cpp

PURPOSE:
Defines logger.cpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in logger.cpp.
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
#include "util/logger.hpp"

#include <atomic>
#include <chrono>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <iomanip>
#include <memory>
#include <mutex>
#include <optional>
#include <regex>
#include <spdlog/async.h>
#include <spdlog/async_logger.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>
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
std::mutex g_component_levels_mutex;
std::unordered_map<std::string, int> g_component_levels;
std::once_flag g_spdlog_init_once;
std::shared_ptr<spdlog::details::thread_pool> g_thread_pool;
std::shared_ptr<spdlog::async_logger> g_async_logger;

const char* level_name(const LogLevel level) noexcept {
    switch (level) {
        case LogLevel::Debug: return "DEBUG";
        case LogLevel::Info: return "INFO";
        case LogLevel::Warning: return "WARNING";
        case LogLevel::Error: return "ERROR";
        case LogLevel::Critical: return "CRITICAL";
        default: return "INFO";
    }
}

int level_number(const LogLevel level) noexcept {
    return static_cast<int>(level);
}

spdlog::level::level_enum to_spdlog_level(const LogLevel level) noexcept {
    switch (level) {
        case LogLevel::Debug: return spdlog::level::debug;
        case LogLevel::Info: return spdlog::level::info;
        case LogLevel::Warning: return spdlog::level::warn;
        case LogLevel::Error: return spdlog::level::err;
        case LogLevel::Critical: return spdlog::level::critical;
        default: return spdlog::level::info;
    }
}

constexpr const char* kRedacted = "***REDACTED***";

bool is_sensitive_key(const std::string& key) {
    std::string lower;
    lower.reserve(key.size());
    for (const char c : key) {
        lower.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(c))));
    }

    static constexpr const char* kSensitiveTokens[] = {
        "password", "passwd", "pwd", "secret", "token", "api_key", "apikey",
        "access_key", "private_key", "auth", "credential", "bearer", "smtp_password",
    };
    for (const char* token : kSensitiveTokens) {
        if (lower.find(token) != std::string::npos) {
            return true;
        }
    }
    return false;
}

std::string redact_text(const std::string& input) {
    static const std::regex kv_pattern(
        R"(\b(password|passwd|pwd|token|secret|api[_-]?key|auth)\b\s*[:=]\s*([^\s,;]+))",
        std::regex::icase);
    static const std::regex bearer_pattern(
        R"(\b(Bearer)\s+([A-Za-z0-9\-._~+/=]+))",
        std::regex::icase);

    std::string out = std::regex_replace(input, kv_pattern, "$1=***REDACTED***");
    out = std::regex_replace(out, bearer_pattern, "$1 ***REDACTED***");
    return out;
}

void redact_extra(LogExtra& extra) {
    for (auto& [key, value] : extra) {
        if (is_sensitive_key(key)) {
            value = kRedacted;
        }
    }
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

void ensure_context_ids(LogExtra& extra) {
    if (!extra.contains("correlation_id")) {
        extra["correlation_id"] = "";
    }
    if (!extra.contains("run_id")) {
        extra["run_id"] = "";
    }
    if (!extra.contains("trace_id")) {
        extra["trace_id"] = "";
    }
}

LogRecord build_record(const LogLevel level, const std::string& message,
                       const std::source_location& location, LogExtra extra) {
    const std::string file_path = location.file_name();
    ensure_context_ids(extra);
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
    record.correlation_id = extra["correlation_id"];
    record.run_id = extra["run_id"];
    record.trace_id = extra["trace_id"];
    record.timestamp = now_timestamp_seconds();
    record.time_repr = now_iso8601_utc();
    record.process_id = process_id();
    record.process_name = process_name();
    record.thread_id = thread_id();
    record.thread_name = thread_name();
    record.extra = std::move(extra);
    return record;
}

void ensure_async_logger_initialized() {
    std::call_once(g_spdlog_init_once, []() {
        constexpr std::size_t kQueueSize = 8192;
        constexpr std::size_t kWorkerThreads = 1;
        g_thread_pool = std::make_shared<spdlog::details::thread_pool>(kQueueSize, kWorkerThreads);

        std::vector<spdlog::sink_ptr> sinks;
        sinks.emplace_back(std::make_shared<spdlog::sinks::stderr_color_sink_mt>());

        g_async_logger = std::make_shared<spdlog::async_logger>(
            "hqt.cpp",
            sinks.begin(),
            sinks.end(),
            g_thread_pool,
            spdlog::async_overflow_policy::overrun_oldest);
        g_async_logger->set_pattern("[CPP][%l] %s:%# %v");
        g_async_logger->set_level(to_spdlog_level(get_log_level()));
        g_async_logger->flush_on(spdlog::level::err);
    });
}

std::string resolve_component(const std::string& module, const LogExtra& extra) {
    const auto it = extra.find("component");
    if (it != extra.end() && !it->second.empty()) {
        return it->second;
    }
    return module;
}

int effective_threshold_for_component(const std::string& component) {
    std::lock_guard<std::mutex> lock(g_component_levels_mutex);
    const auto it = g_component_levels.find(component);
    if (it != g_component_levels.end()) {
        return it->second;
    }
    return g_log_level.load(std::memory_order_relaxed);
}

bool force_throw_enabled(const char* key) {
    const char* value = std::getenv(key);
    return value != nullptr && std::string(value) == "1";
}

}  // namespace

void set_log_level(const LogLevel level) noexcept {
    g_log_level.store(static_cast<int>(level), std::memory_order_relaxed);
    try {
        if (force_throw_enabled("HQT_LOGGER_TEST_THROW_SET_LEVEL")) {
            throw std::runtime_error("forced set_log_level failure");
        }
        ensure_async_logger_initialized();
        if (g_async_logger) {
            g_async_logger->set_level(to_spdlog_level(level));
        }
    } catch (...) {}
}

LogLevel get_log_level() noexcept {
    return static_cast<LogLevel>(g_log_level.load(std::memory_order_relaxed));
}

void set_component_log_level(const std::string& component, const LogLevel level) {
    std::lock_guard<std::mutex> lock(g_component_levels_mutex);
    g_component_levels[component] = static_cast<int>(level);
}

void clear_component_log_level(const std::string& component) {
    std::lock_guard<std::mutex> lock(g_component_levels_mutex);
    g_component_levels.erase(component);
}

void clear_all_component_log_levels() {
    std::lock_guard<std::mutex> lock(g_component_levels_mutex);
    g_component_levels.clear();
}

std::optional<LogLevel> get_component_log_level(const std::string& component) {
    std::lock_guard<std::mutex> lock(g_component_levels_mutex);
    const auto it = g_component_levels.find(component);
    if (it == g_component_levels.end()) {
        return std::nullopt;
    }
    return static_cast<LogLevel>(it->second);
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

void flush_logs() noexcept {
    try {
        if (force_throw_enabled("HQT_LOGGER_TEST_THROW_FLUSH")) {
            throw std::runtime_error("forced flush failure");
        }
        ensure_async_logger_initialized();
        if (g_async_logger) {
            g_async_logger->flush();
        }
    } catch (...) {}
}

void log(const LogLevel level, const std::string& message,
         const std::source_location& location, LogExtra extra) {
    redact_extra(extra);
    const std::string safe_message = redact_text(message);
    const std::string component = resolve_component(module_from_path(location.file_name()), extra);
    if (static_cast<int>(level) < effective_threshold_for_component(component)) {
        return;
    }

    LogRecord record = build_record(level, safe_message, location, std::move(extra));

    LogSink sink_copy;
    {
        std::lock_guard<std::mutex> lock(g_sink_mutex);
        sink_copy = g_sink;
    }

    if (sink_copy) {
        sink_copy(record);
    }

    if (g_stderr_enabled.load(std::memory_order_relaxed)) {
        try {
            if (force_throw_enabled("HQT_LOGGER_TEST_THROW_STDERR_LOG")) {
                throw std::runtime_error("forced stderr log failure");
            }
            ensure_async_logger_initialized();
            if (g_async_logger) {
                g_async_logger->log(
                    spdlog::source_loc{
                        location.file_name(),
                        static_cast<int>(location.line()),
                        location.function_name()},
                    to_spdlog_level(level),
                    safe_message);
            }
        } catch (...) {}
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

void critical(const std::string& message, const std::source_location& location,
              LogExtra extra) {
    log(LogLevel::Critical, message, location, std::move(extra));
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

