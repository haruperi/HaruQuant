#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>

#include "util/error.hpp"

namespace nb = nanobind;

void register_core_bindings(nb::module_& m);

NB_MODULE(haruquant, m) {
    m.doc() = "HaruQuant Core Module";

    m.def("error_from_retcode", [](int code) {
        const auto info = haruquant::util::error_from_retcode(code);
        nb::dict out;
        out["code"] = info.code;
        out["name"] = info.name;
        out["message"] = info.message;
        out["domain"] = info.domain;
        out["retryable"] = info.retryable;
        return out;
    }, "Return structured error taxonomy payload for a trade retcode.");

    m.def("error_name", &haruquant::util::error_name,
          "Return taxonomy error name for a trade retcode.");

    nb::module_ core = m.def_submodule("core", "Core engine bindings");
    register_core_bindings(core);
}
