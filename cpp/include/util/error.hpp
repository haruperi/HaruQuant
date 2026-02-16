/**
 * @file error.hpp
 * @brief Shared error taxonomy for C++ core and Python bridge.
 */

#pragma once

#include <string>

namespace hqt::util {

struct ErrorInfo {
    int code{0};
    std::string name{"OK"};
    std::string message{"The operation completed successfully"};
    std::string domain{"trade"};
    bool retryable{false};
};

[[nodiscard]] ErrorInfo error_from_retcode(int code);
[[nodiscard]] std::string error_name(int code);
[[nodiscard]] bool is_success_retcode(int code) noexcept;

}  // namespace hqt::util

