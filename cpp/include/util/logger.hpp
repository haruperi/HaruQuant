/**
FILE: include\util\logger.hpp

PURPOSE:
Defines logger.hpp functionality used by the C++ runtime and bridge layers.

RESPONSIBILITIES:
- Own file-level logic for this compilation or declaration unit.
- Keep module boundaries clear for related engine/trading/risk/util flows.
- Provide stable behavior expected by callers and tests.

MAIN COMPONENTS:
- Primary types/functions declared or defined in logger.hpp.
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
#pragma once

#include <functional>
#include <cstdint>
#include <map>
#include <source_location>
#include <string>
#include <optional>

namespace haruquant::util {

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

}  // namespace haruquant::util

