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
option(HQT_ENABLE_ASAN "Enable AddressSanitizer instrumentation for C++ targets" OFF)

if(HQT_ENABLE_ASAN)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
        add_link_options(-fsanitize=address)
        message(STATUS "HQT_ENABLE_ASAN=ON (compiler: ${CMAKE_CXX_COMPILER_ID})")
    else()
        message(WARNING "HQT_ENABLE_ASAN requested, but compiler '${CMAKE_CXX_COMPILER_ID}' is not configured for ASan flags in this project.")
    endif()
endif()

# C++ core library
add_subdirectory(cpp)

# Python bridge module
if(HQT_BUILD_BRIDGE)
    add_subdirectory(bridge)
endif()
