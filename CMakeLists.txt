cmake_minimum_required(VERSION 3.21)

# Auto-wire vcpkg toolchain when CMake is configured directly without
# explicit -DCMAKE_TOOLCHAIN_FILE (common in IDE configure flows).
if(NOT DEFINED CMAKE_TOOLCHAIN_FILE)
    if(DEFINED ENV{VCPKG_ROOT} AND EXISTS "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake")
        set(CMAKE_TOOLCHAIN_FILE
            "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake"
            CACHE FILEPATH "vcpkg toolchain file" FORCE)
    elseif(EXISTS "C:/vcpkg/scripts/buildsystems/vcpkg.cmake")
        set(CMAKE_TOOLCHAIN_FILE
            "C:/vcpkg/scripts/buildsystems/vcpkg.cmake"
            CACHE FILEPATH "vcpkg toolchain file" FORCE)
    endif()
endif()

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
option(HQT_ENABLE_COVERAGE "Enable coverage instrumentation for C++ targets (GCC/Clang)" OFF)

if(HQT_ENABLE_ASAN)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
        add_link_options(-fsanitize=address)
        message(STATUS "HQT_ENABLE_ASAN=ON (compiler: ${CMAKE_CXX_COMPILER_ID})")
    else()
        message(WARNING "HQT_ENABLE_ASAN requested, but compiler '${CMAKE_CXX_COMPILER_ID}' is not configured for ASan flags in this project.")
    endif()
endif()

if(HQT_ENABLE_COVERAGE)
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang|GNU")
        add_compile_options(-O0 -g --coverage)
        add_link_options(--coverage)
        message(STATUS "HQT_ENABLE_COVERAGE=ON (compiler: ${CMAKE_CXX_COMPILER_ID})")
    else()
        message(WARNING "HQT_ENABLE_COVERAGE requested, but compiler '${CMAKE_CXX_COMPILER_ID}' is not configured for coverage flags in this project.")
    endif()
endif()

# C++ core library
add_subdirectory(cpp)

# Python bridge module
if(HQT_BUILD_BRIDGE)
    add_subdirectory(bridge)
endif()
