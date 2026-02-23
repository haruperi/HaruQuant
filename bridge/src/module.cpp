#include <nanobind/nanobind.h>

namespace nb = nanobind;

void register_core_bindings(nb::module_& m);

NB_MODULE(haruquant, m) {
    m.doc() = "HaruQuant Core Module";
    nb::module_ core = m.def_submodule("core", "Core engine bindings");
    register_core_bindings(core);
}

