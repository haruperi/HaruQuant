#include <nanobind/nanobind.h>

namespace nb = nanobind;

void register_core_bindings(nb::module_& m) {
    m.doc() = "Core engine bindings";
}
