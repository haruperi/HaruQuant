#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <hqt/hello.hpp>

namespace nb = nanobind;

void register_sim_bindings(nb::module_& m);

NB_MODULE(hqt_engine, m) {
    m.doc() = "HQT Engine - C++ core for HaruQuant";

    m.def("hello", &hqt::hello, "Returns the engine version string.");

    nb::class_<hqt::Version>(m, "Version")
        .def_ro("major", &hqt::Version::major)
        .def_ro("minor", &hqt::Version::minor)
        .def_ro("patch", &hqt::Version::patch)
        .def("__repr__", [](const hqt::Version& v) {
            return "Version(" + std::to_string(v.major) + ", "
                   + std::to_string(v.minor) + ", "
                   + std::to_string(v.patch) + ")";
        });

    m.def("version", &hqt::version, "Returns the engine version struct.");

    nb::module_ sim = m.def_submodule("sim", "Simulation engine bindings");
    register_sim_bindings(sim);
}
