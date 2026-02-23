#include <nanobind/nanobind.h>

#include "core/backtest_simulator.hpp"

namespace nb = nanobind;

void register_core_bindings(nb::module_& m) {
    m.doc() = "Core engine bindings";

    nb::class_<haruquant::core::BacktestSimulator>(m, "BacktestSimulator")
        .def(nb::init<>());
}

