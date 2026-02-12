cmake_minimum_required(VERSION 3.21)
project(HQT VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Export compile_commands.json for IDE support
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Enable testing at top level so CTest discovers tests from subdirectories
enable_testing()

# Build options
option(HQT_BUILD_TESTS "Build C++ tests" ON)
option(HQT_BUILD_BENCHMARKS "Build C++ benchmarks" ON)
option(HQT_BUILD_BRIDGE "Build Python bridge (nanobind)" ON)

# C++ core library
add_subdirectory(cpp)

# Python bridge module
if(HQT_BUILD_BRIDGE)
    add_subdirectory(bridge)
endif()
