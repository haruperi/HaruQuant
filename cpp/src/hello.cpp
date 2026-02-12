#include <hqt/hello.hpp>

namespace hqt {

std::string hello() {
    return "HQT Engine v0.1.0";
}

Version version() {
    return {0, 1, 0};
}

} // namespace hqt
