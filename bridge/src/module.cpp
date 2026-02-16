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

void dispatch_log_to_python(const hqt::util::LogRecord& record) {
    nb::gil_scoped_acquire gil;

    nb::object callback;
    {
        std::lock_guard<std::mutex> lock(g_log_callback_mutex);
        callback = g_log_callback;
    }

    if (callback.ptr() == nullptr || callback.is_none()) {
        return;
    }

    nb::dict extra_dict;
    for (const auto& [k, v] : record.extra) {
        extra_dict[nb::str(k.c_str())] = nb::str(v.c_str());
    }

    nb::dict payload;
    nb::dict elapsed_dict;
    elapsed_dict["seconds"] = 0.0;
    elapsed_dict["repr"] = "0:00:00";
    payload["elapsed"] = elapsed_dict;
    payload["exception"] = nb::none();
    payload["extra"] = extra_dict;
    nb::dict file_dict;
    file_dict["name"] = nb::str(record.file_name.c_str());
    file_dict["path"] = nb::str(record.file_path.c_str());
    payload["file"] = file_dict;
    payload["function"] = nb::str(record.function.c_str());
    nb::dict level_dict;
    level_dict["name"] = nb::str(record.level_name.c_str());
    level_dict["no"] = record.level_no;
    level_dict["icon"] = "";
    payload["level"] = level_dict;
    payload["line"] = record.line;
    payload["message"] = nb::str(record.message.c_str());
    payload["module"] = nb::str(record.module.c_str());
    payload["name"] = nb::str(record.logger_name.c_str());
    nb::dict process_dict;
    process_dict["id"] = record.process_id;
    process_dict["name"] = nb::str(record.process_name.c_str());
    payload["process"] = process_dict;
    nb::dict thread_dict;
    thread_dict["id"] = record.thread_id;
    thread_dict["name"] = nb::str(record.thread_name.c_str());
    payload["thread"] = thread_dict;
    nb::dict time_dict;
    time_dict["timestamp"] = record.timestamp;
    time_dict["repr"] = nb::str(record.time_repr.c_str());
    payload["time"] = time_dict;

    try {
        // Preferred path: callback(record_dict)
        callback(payload);
    } catch (...) {
        // Backward compatibility: callback(level, message)
        try {
            callback(nb::str(record.level_name.c_str()), nb::str(record.message.c_str()));
        } catch (...) {
            // Logging should never throw back into execution code.
        }
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
