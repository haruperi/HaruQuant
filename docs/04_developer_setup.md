# Developer Setup Guide

| Field           | Detail                  |
|-----------------|-------------------------|
| **Document ID** | DEV-HQTBS-001           |
| **Version**     | 1.0.0                   |
| **Date**        | 2026-02-12              |
| **Phase**       | 0 (C++ Build System)    |

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository Setup](#2-repository-setup)
3. [C++ Build System](#3-c-build-system)
4. [Python Environment](#4-python-environment)
5. [Building the C++ Engine](#5-building-the-c-engine)
6. [Running Tests](#6-running-tests)
7. [Project Structure](#7-project-structure)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Prerequisites

### Windows (Primary Development Platform)

| Tool | Version | Location |
|------|---------|----------|
| Visual Studio 2026 (v18) | Community or higher | `C:\Program Files\Microsoft Visual Studio\18\Community` |
| MSVC Toolset | 14.50+ | Installed with VS "Desktop development with C++" workload |
| CMake | 4.1+ | Installed with VS or standalone from cmake.org |
| vcpkg | Latest | `C:\vcpkg` |
| Python | 3.9+ (tested with 3.14) | Virtual environment in `venv/` |
| Git | 2.x | git-scm.com |

### Linux (Future Support)

| Tool | Version | Notes |
|------|---------|-------|
| GCC | 12+ (C++20 support) | `sudo apt install g++-12` or newer |
| CMake | 3.21+ | `sudo apt install cmake` |
| vcpkg | Latest | Clone to `~/vcpkg` or `/opt/vcpkg` |
| Python | 3.9+ | System or pyenv |
| Git | 2.x | `sudo apt install git` |

---

## 2. Repository Setup

```bash
# Clone the repository
git clone https://github.com/haruperi/HaruQuant.git
cd HaruQuant

# Create Python virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/macOS)
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
pip install nanobind
```

---

## 3. C++ Build System

### Architecture

The C++ build uses CMake with vcpkg for dependency management and Nanobind for Python interop:

```
CMakeLists.txt          # Top-level orchestrator
├── cpp/CMakeLists.txt  # hqt_core static library + tests + benchmarks
└── bridge/CMakeLists.txt  # hqt_engine Python module (Nanobind)
```

### vcpkg Dependencies

Defined in `vcpkg.json` at the project root. Installed automatically during CMake configure via manifest mode:

| Package | Version | Purpose |
|---------|---------|---------|
| gtest | 1.17+ | C++ unit testing |
| benchmark | 1.9+ | C++ micro-benchmarking |
| spdlog | 1.17+ | C++ async logging (Phase 2+) |
| tomlplusplus | 3.4+ | TOML config parsing (Phase 2+) |

### Nanobind

Installed via pip (not vcpkg). Nanobind generates a Python-importable extension module (`hqt_engine.pyd` on Windows, `hqt_engine.so` on Linux) using the Stable ABI for cross-version compatibility.

```bash
pip install nanobind
```

---

## 4. Python Environment

The project uses a virtual environment at `venv/`. Key Python packages:

```bash
# Core dependencies
pip install -r requirements.txt

# C++ bridge dependency
pip install nanobind

# Verify nanobind installation
python -c "import nanobind; print(nanobind.cmake_dir())"
```

---

## 5. Building the C++ Engine

### Using the Build Script (Recommended)

```bash
# Default: configure + build Release
python scripts/build_cpp.py

# Build in Debug mode
python scripts/build_cpp.py --debug

# Configure only (no build)
python scripts/build_cpp.py --configure

# Build only (skip configure, use after --configure)
python scripts/build_cpp.py --build

# Build + run all C++ tests
python scripts/build_cpp.py --test

# Build + copy hqt_engine module to project root
python scripts/build_cpp.py --install

# Remove build directory
python scripts/build_cpp.py --clean
```

### Linux Build Script

```bash
chmod +x scripts/build_cpp.sh
./scripts/build_cpp.sh          # Configure + build Release
./scripts/build_cpp.sh --test   # Build + run tests
./scripts/build_cpp.sh --debug  # Build in Debug mode
```

The Linux script auto-detects vcpkg from `$VCPKG_ROOT`, `~/vcpkg`, or `/opt/vcpkg`.

### Manual CMake Commands

#### Windows

```cmd
cmake -B build -S . ^
    -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake ^
    -G "Visual Studio 18 2026" ^
    -A x64

cmake --build build --config Release --parallel
```

#### Linux

```bash
cmake -B build -S . \
    -DCMAKE_TOOLCHAIN_FILE=$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -G "Unix Makefiles"

cmake --build build --config Release --parallel $(nproc)
```

### Build Outputs

After a successful build:

| Output | Location | Description |
|--------|----------|-------------|
| `hqt_core.lib` / `libhqt_core.a` | `build/cpp/Release/` | C++ static library |
| `hqt_engine.pyd` / `hqt_engine.so` | `build/bridge/Release/` | Python extension module |
| `hqt_tests` | `build/cpp/tests/Release/` | Google Test executable |
| `hqt_benchmarks` | `build/cpp/benchmarks/Release/` | Google Benchmark executable |

### CMake Options

| Option | Default | Description |
|--------|---------|-------------|
| `HQT_BUILD_TESTS` | `ON` | Build C++ unit tests |
| `HQT_BUILD_BENCHMARKS` | `ON` | Build C++ benchmarks |
| `HQT_BUILD_BRIDGE` | `ON` | Build Nanobind Python module |

Example: build without benchmarks:
```bash
cmake -B build -S . -DHQT_BUILD_BENCHMARKS=OFF ...
```

---

## 6. Running Tests

### C++ Tests (Google Test)

```bash
# Via CTest (from project root)
ctest --test-dir build -C Release --output-on-failure

# Direct execution (more verbose)
./build/cpp/tests/Release/hqt_tests          # Windows
./build/cpp/tests/hqt_tests                   # Linux
```

### Python Bridge Tests

```bash
# Run bridge tests
python -m pytest tests/unit/test_hqt_engine.py -v --no-cov
```

### C++ Benchmarks

```bash
# Run all benchmarks
./build/cpp/benchmarks/Release/hqt_benchmarks     # Windows
./build/cpp/benchmarks/hqt_benchmarks              # Linux

# Run with minimum time
./build/cpp/benchmarks/Release/hqt_benchmarks --benchmark_min_time=1s
```

### Quick Verification

```bash
# Verify the full pipeline in one command
python scripts/build_cpp.py --test

# Verify Python can import the C++ module
python -c "import sys; sys.path.insert(0, 'build/bridge/Release'); import hqt_engine; print(hqt_engine.hello())"
# Expected output: HQT Engine v0.1.0
```

---

## 7. Project Structure

```
HaruQuant/
├── CMakeLists.txt              # Top-level CMake (C++20, vcpkg, testing)
├── vcpkg.json                  # vcpkg dependency manifest
│
├── cpp/                        # C++ Core Engine
│   ├── CMakeLists.txt          # hqt_core static library
│   ├── include/hqt/            # Public headers
│   │   └── hello.hpp           # Version API
│   ├── src/                    # Implementation files
│   │   └── hello.cpp
│   ├── tests/                  # Google Test suites
│   │   ├── CMakeLists.txt
│   │   └── test_hello.cpp
│   └── benchmarks/             # Google Benchmark suites
│       ├── CMakeLists.txt
│       └── bench_hello.cpp
│
├── bridge/                     # Nanobind Python Bridge
│   ├── CMakeLists.txt          # Nanobind module build
│   └── src/
│       └── module.cpp          # hqt_engine module definition
│
├── apps/                       # Python application modules
├── tests/                      # Python test suites
│   └── unit/
│       └── test_hqt_engine.py  # Bridge verification tests
├── scripts/
│   ├── build_cpp.py            # Windows build script
│   └── build_cpp.sh            # Linux/macOS build script
├── config/                     # Configuration files
├── docs/                       # Documentation
├── data/                       # Data storage
└── venv/                       # Python virtual environment
```

---

## 8. Troubleshooting

### CMake cannot find vcpkg

```
CMake Error: CMAKE_TOOLCHAIN_FILE not found
```

**Fix:** Verify vcpkg location and pass the correct path:
```bash
# Windows - verify vcpkg exists
dir C:\vcpkg\scripts\buildsystems\vcpkg.cmake

# Linux - set VCPKG_ROOT
export VCPKG_ROOT=$HOME/vcpkg
```

### CMake cannot find Python

```
Could not find a package configuration file provided by "Python"
```

**Fix:** Ensure the virtual environment is activated before running CMake:
```bash
# Windows
venv\Scripts\activate
python scripts/build_cpp.py

# Linux
source venv/bin/activate
python scripts/build_cpp.py
```

### nanobind not found

```
FATAL_ERROR: nanobind not found. Install it with: pip install nanobind
```

**Fix:**
```bash
pip install nanobind
python -c "import nanobind; print(nanobind.cmake_dir())"  # Verify
```

### CTest reports "No tests found"

This happens if `enable_testing()` is not in the top-level `CMakeLists.txt`. Verify the top-level file contains:
```cmake
enable_testing()
```

### Python import fails with TypeError

```
TypeError: Unable to convert function return value to a Python type!
```

**Fix:** Ensure `bridge/src/module.cpp` includes the required nanobind STL headers:
```cpp
#include <nanobind/stl/string.h>    // For std::string
#include <nanobind/stl/vector.h>    // For std::vector (when needed)
```

### MSVC version mismatch

If CMake picks the wrong Visual Studio version, specify the generator explicitly:
```bash
cmake -B build -S . -G "Visual Studio 18 2026" -A x64 ...
```

### Build fails on Linux with "filesystem not found"

For older GCC versions, you may need to link `stdc++fs`:
```cmake
target_link_libraries(hqt_core PRIVATE stdc++fs)
```

---

*End of Document — DEV-HQTBS-001 v1.0.0*
