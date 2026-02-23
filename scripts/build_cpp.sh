#!/usr/bin/env bash
# Build script for HQT C++ engine (Linux/macOS).
#
# Usage:
#   ./scripts/build_cpp.sh              # Configure + build Release
#   ./scripts/build_cpp.sh --debug      # Configure + build Debug
#   ./scripts/build_cpp.sh --configure  # Configure only
#   ./scripts/build_cpp.sh --build      # Build only (skip configure)
#   ./scripts/build_cpp.sh --test       # Build + run tests
#   ./scripts/build_cpp.sh --coverage   # Build + run tests + enforce coverage gate
#   ./scripts/build_cpp.sh --clean      # Remove build directory
#   ./scripts/build_cpp.sh --install    # Build + copy module to project root

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
BUILD_TYPE="Release"
ENABLE_COVERAGE=0

# Detect vcpkg - check VCPKG_ROOT env var, then common locations
if [ -n "${VCPKG_ROOT:-}" ]; then
    VCPKG_TOOLCHAIN="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake"
elif [ -d "$HOME/vcpkg" ]; then
    VCPKG_TOOLCHAIN="$HOME/vcpkg/scripts/buildsystems/vcpkg.cmake"
elif [ -d "/opt/vcpkg" ]; then
    VCPKG_TOOLCHAIN="/opt/vcpkg/scripts/buildsystems/vcpkg.cmake"
else
    echo "ERROR: vcpkg not found. Set VCPKG_ROOT or install to ~/vcpkg or /opt/vcpkg"
    exit 1
fi

run() {
    echo ""
    echo ">>> $*"
    "$@"
}

do_configure() {
    mkdir -p "$BUILD_DIR"
    local coverage_flag="OFF"
    local bridge_flag="ON"
    local bench_flag="ON"
    if [ "$ENABLE_COVERAGE" -eq 1 ]; then
        coverage_flag="ON"
        bridge_flag="OFF"
        bench_flag="OFF"
    fi
    run cmake \
        -B "$BUILD_DIR" \
        -S "$PROJECT_ROOT" \
        -DCMAKE_TOOLCHAIN_FILE="$VCPKG_TOOLCHAIN" \
        -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
        -DHQT_ENABLE_COVERAGE="$coverage_flag" \
        -DHQT_BUILD_BRIDGE="$bridge_flag" \
        -DHQT_BUILD_BENCHMARKS="$bench_flag" \
        -G "Unix Makefiles"
}

do_build() {
    run cmake --build "$BUILD_DIR" --config "$BUILD_TYPE" --parallel "$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"
}

do_test() {
    run ctest --test-dir "$BUILD_DIR" -C "$BUILD_TYPE" --output-on-failure
}

do_coverage_check() {
    run python3 -m pip install --upgrade gcovr
    run python3 "$PROJECT_ROOT/scripts/check_cpp_coverage.py" \
        --root "$PROJECT_ROOT" \
        --build-dir "build" \
        --threshold-file "cpp/coverage_thresholds.json" \
        --gcovr-html "build/coverage/index.html"
}

do_install() {
    # Find and copy the built module (.so on Linux, .dylib on macOS)
    local found=0
    for ext in so dylib; do
        for f in $(find "$BUILD_DIR" -name "hqt_engine*.$ext" 2>/dev/null); do
            cp "$f" "$PROJECT_ROOT/"
            echo "Installed: $(basename "$f") -> $PROJECT_ROOT/"
            found=1
            break 2
        done
    done
    if [ $found -eq 0 ]; then
        echo "WARNING: Could not find built hqt_engine module"
    fi
}

do_clean() {
    if [ -d "$BUILD_DIR" ]; then
        rm -rf "$BUILD_DIR"
        echo "Removed $BUILD_DIR"
    else
        echo "Build directory does not exist"
    fi
}

# Parse arguments
ACTION="default"
for arg in "$@"; do
    case "$arg" in
        --debug)     BUILD_TYPE="Debug" ;;
        --configure) ACTION="configure" ;;
        --build)     ACTION="build" ;;
        --test)      ACTION="test" ;;
        --coverage)  ACTION="coverage"; ENABLE_COVERAGE=1; BUILD_TYPE="Debug" ;;
        --clean)     ACTION="clean" ;;
        --install)   ACTION="install" ;;
        --help|-h)
            echo "Usage: $0 [--debug] [--configure|--build|--test|--coverage|--clean|--install]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: $0 [--debug] [--configure|--build|--test|--coverage|--clean|--install]"
            exit 1
            ;;
    esac
done

case "$ACTION" in
    clean)     do_clean ;;
    configure) do_configure ;;
    build)     do_build ;;
    test)      do_configure && do_build && do_test ;;
    coverage)  do_configure && do_build && do_test && do_coverage_check ;;
    install)   do_configure && do_build && do_install ;;
    default)   do_configure && do_build ;;
esac
