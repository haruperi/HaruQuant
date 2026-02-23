# Find Python and nanobind
find_package(Python 3.9
    REQUIRED COMPONENTS Interpreter Development.Module
    OPTIONAL_COMPONENTS Development.SABIModule
)

# Find nanobind installed via pip
execute_process(
    COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
    OUTPUT_STRIP_TRAILING_WHITESPACE
    OUTPUT_VARIABLE nanobind_ROOT
    RESULT_VARIABLE nanobind_RESULT
)
if(NOT nanobind_RESULT EQUAL 0)
    message(FATAL_ERROR "nanobind not found. Install it with: pip install nanobind")
endif()

find_package(nanobind CONFIG REQUIRED)

# Build the Python extension module
nanobind_add_module(haruquant
    STABLE_ABI
    src/module.cpp
    src/sim_bindings.cpp
    src/risk_bindings.cpp
)

target_link_libraries(haruquant PRIVATE hqt_core)

# Install the module next to the bridge source for easy import
install(TARGETS haruquant LIBRARY DESTINATION .)
