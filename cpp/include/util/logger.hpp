/**
 * @file logger.hpp
 * @brief Minimal process-wide logger for C++ core and bridge forwarding.
 */

#pragma once

#include <functional>
#include <string>

namespace hqt::util {

enum class LogLevel {
    Debug = 10,
    Info = 20,
    Warning = 30,
    Error = 40,
};

using LogSink = std::function<void(LogLevel, const std::string&)>;

void set_log_level(LogLevel level) noexcept;
[[nodiscard]] LogLevel get_log_level() noexcept;

void set_stderr_logging(bool enabled) noexcept;
[[nodiscard]] bool stderr_logging_enabled() noexcept;

void set_log_sink(LogSink sink);

void log(LogLevel level, const std::string& message);

void debug(const std::string& message);
void info(const std::string& message);
void warning(const std::string& message);
void error(const std::string& message);

}  // namespace hqt::util
