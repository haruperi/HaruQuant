#pragma once

#include <string>

namespace hqt {

struct Version {
    int major;
    int minor;
    int patch;
};

std::string hello();
Version version();

} // namespace hqt
