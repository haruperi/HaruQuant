#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <usage/logger_usage.hpp>
#include <hqt/hello.hpp>
#include <util/logger.hpp>

#include <algorithm>
#include <cctype>
#include <mutex>
#include <string>

namespace nb = nanobind;

void register_sim_bindings(nb::module_& m);

namespace {

std::mutex g_log_callback_mutex;
nb::object g_log_callback;

std::string level_to_string(const hqt::util::LogLevel level) {
    switch (level) {
        case hqt::util::LogLevel::Debug: return "DEBUG";
        case hqt::util::LogLevel::Info: return "INFO";
        case hqt::util::LogLevel::Warning: return "WARNING";
        case hqt::util::LogLevel::Error: return "ERROR";
        default: return "INFO";
    }
}

hqt::util::LogLevel parse_level(const std::string& raw_level) {
    std::string level = raw_level;
    std::transform(level.begin(), level.end(), level.begin(), [](unsigned char c) {
        return static_cast<char>(std::tolower(c));
    });

    if (level == "debug") {
        return hqt::util::LogLevel::Debug;
    }
    if (level == "info") {
        return hqt::util::LogLevel::Info;
    }
    if (level == "warning" || level == "warn") {
        return hqt::util::LogLevel::Warning;
    }
    if (level == "error") {
        return hqt::util::LogLevel::Error;
    }

    throw nb::value_error("Invalid C++ log level. Use debug|info|warning|error.");
}

void dispatch_log_to_python(const hqt::util::LogLevel level, const std::string& message) {
    nb::gil_scoped_acquire gil;

    nb::object callback;
    {
        std::lock_guard<std::mutex> lock(g_log_callback_mutex);
        callback = g_log_callback;
    }

    if (callback.ptr() == nullptr || callback.is_none()) {
        return;
    }

    try {
        callback(level_to_string(level), message);
    } catch (...) {
        // Logging should never throw back into execution code.
    }
}

}  // namespace

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
    m.def("set_log_level", [](const std::string& level) {
        hqt::util::set_log_level(parse_level(level));
    }, "Set C++ logger level: debug|info|warning|error.");
    m.def("set_stderr_logging", &hqt::util::set_stderr_logging,
          "Enable/disable direct C++ stderr logging.");
    m.def("set_log_callback", [](nb::object callback) {
        if (callback.is_none()) {
            {
                std::lock_guard<std::mutex> lock(g_log_callback_mutex);
                g_log_callback = nb::object();
            }
            hqt::util::set_log_sink(hqt::util::LogSink{});
            return;
        }

        if (!PyCallable_Check(callback.ptr())) {
            throw nb::type_error("set_log_callback expects a callable or None.");
        }

        {
            std::lock_guard<std::mutex> lock(g_log_callback_mutex);
            g_log_callback = std::move(callback);
        }

        hqt::util::set_log_sink(dispatch_log_to_python);
    }, nb::arg("callback").none(),
       "Set Python callback(level: str, message: str) for C++ logs. Pass None to clear.");
    m.def("emit_log", [](const std::string& level, const std::string& message) {
        hqt::util::log(parse_level(level), message);
    }, "Emit a C++ log message (primarily for integration testing).");
    m.def("run_cpp_logger_usage_example", &hqt::usage::run_logger_usage_example,
          "Run minimal C++ logger usage example.");

    nb::module_ sim = m.def_submodule("sim", "Simulation engine bindings");
    register_sim_bindings(sim);
}
