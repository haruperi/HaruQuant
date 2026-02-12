#pragma once

#include <string>

namespace hqt {

/// Returns the engine version string.
std::string hello();

/// Returns the engine version as a structured triple.
struct Version {
    int major;
    int minor;
    int patch;
};

Version version();

} // namespace hqt
