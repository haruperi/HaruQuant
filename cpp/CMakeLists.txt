cmake_minimum_required(VERSION 3.21)

# Standalone mode (when opening `cpp/` directly in IDEs).
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
    # Auto-wire vcpkg toolchain for direct `cpp/` configure runs.
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

    # Point manifest mode to repo root where vcpkg.json lives.
    if(NOT DEFINED VCPKG_MANIFEST_DIR)
        set(VCPKG_MANIFEST_DIR
            "${CMAKE_CURRENT_LIST_DIR}/.."
            CACHE PATH "vcpkg manifest directory" FORCE)
    endif()

    project(HQT_CPP VERSION 0.1.0 LANGUAGES CXX)

    set(CMAKE_CXX_STANDARD 20)
    set(CMAKE_CXX_STANDARD_REQUIRED ON)
    set(CMAKE_CXX_EXTENSIONS OFF)

    option(HQT_BUILD_TESTS "Build C++ tests" ON)
    option(HQT_BUILD_BENCHMARKS "Build C++ benchmarks" OFF)

    if(NOT DEFINED VCPKG_TARGET_TRIPLET)
        set(VCPKG_TARGET_TRIPLET "x64-windows")
    endif()

    # Help CMake find vcpkg-installed packages even if toolchain is not injected.
    list(APPEND CMAKE_PREFIX_PATH "${CMAKE_BINARY_DIR}/vcpkg_installed/${VCPKG_TARGET_TRIPLET}")
    if(DEFINED ENV{VCPKG_ROOT})
        list(APPEND CMAKE_PREFIX_PATH "$ENV{VCPKG_ROOT}/installed/${VCPKG_TARGET_TRIPLET}")
    endif()
    if(EXISTS "C:/vcpkg/installed/${VCPKG_TARGET_TRIPLET}")
        list(APPEND CMAKE_PREFIX_PATH "C:/vcpkg/installed/${VCPKG_TARGET_TRIPLET}")
    endif()
endif()

# Fallback package path for manifest-mode installs under the current build tree.
if(NOT DEFINED VCPKG_TARGET_TRIPLET)
    set(VCPKG_TARGET_TRIPLET "x64-windows")
endif()
list(APPEND CMAKE_PREFIX_PATH "${CMAKE_BINARY_DIR}/vcpkg_installed/${VCPKG_TARGET_TRIPLET}")

# HQT Core C++ Library
find_package(spdlog CONFIG REQUIRED)

add_library(haruquant_core STATIC
    src/core/backtest_simulator.cpp
    src/engine/engine.cpp
    src/engine/trading.cpp
    src/engine/analytics.cpp
    src/util/error_description.cpp
    src/util/logger.cpp
    src/usage/usage.cpp
    src/risk/risk_engine.cpp
    src/util/validators.cpp
    src/trading/trade.cpp
)

target_include_directories(haruquant_core PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(haruquant_core PUBLIC cxx_std_20)
target_link_libraries(haruquant_core PRIVATE spdlog::spdlog)

# MSVC-specific flags
if(MSVC)
    target_compile_options(haruquant_core PRIVATE /W4 /utf-8)
else()
    target_compile_options(haruquant_core PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Tests
if(HQT_BUILD_TESTS)
    enable_testing()
    add_subdirectory(tests)
endif()

# Benchmarks
if(HQT_BUILD_BENCHMARKS)
    add_subdirectory(benchmarks)
endif()
