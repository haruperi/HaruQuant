/**
 * @file logger.hpp
 * @brief Minimal process-wide logger for C++ core and bridge forwarding.
 */

#pragma once

#include <functional>
#include <cstdint>
#include <map>
#include <source_location>
#include <string>
#include <optional>

namespace hqt::util {

enum class LogLevel {
    Debug = 10,
    Info = 20,
    Warning = 30,
    Error = 40,
    Critical = 50,
};

using LogExtra = std::map<std::string, std::string>;

struct LogRecord {
    std::string logger_name;
    std::string module;
    std::string file_name;
    std::string file_path;
    std::string function;
    int line;

    std::string level_name;
    int level_no;
    std::string message;
    std::string correlation_id;
    std::string run_id;
    std::string trace_id;

    double timestamp;
    std::string time_repr;

    int process_id;
    std::string process_name;
    std::uint64_t thread_id;
    std::string thread_name;

    LogExtra extra;
};

using LogSink = std::function<void(const LogRecord&)>;

void set_log_level(LogLevel level) noexcept;
[[nodiscard]] LogLevel get_log_level() noexcept;
void set_component_log_level(const std::string& component, LogLevel level);
void clear_component_log_level(const std::string& component);
void clear_all_component_log_levels();
[[nodiscard]] std::optional<LogLevel> get_component_log_level(const std::string& component);

void set_stderr_logging(bool enabled) noexcept;
[[nodiscard]] bool stderr_logging_enabled() noexcept;

void set_log_sink(LogSink sink);
void flush_logs() noexcept;

void log(LogLevel level, const std::string& message,
         const std::source_location& location = std::source_location::current(),
         LogExtra extra = {});

void debug(const std::string& message,
           const std::source_location& location = std::source_location::current(),
           LogExtra extra = {});
void info(const std::string& message,
          const std::source_location& location = std::source_location::current(),
          LogExtra extra = {});
void warning(const std::string& message,
             const std::source_location& location = std::source_location::current(),
             LogExtra extra = {});
void error(const std::string& message,
           const std::source_location& location = std::source_location::current(),
           LogExtra extra = {});
void critical(const std::string& message,
              const std::source_location& location = std::source_location::current(),
              LogExtra extra = {});

}  // namespace hqt::util
