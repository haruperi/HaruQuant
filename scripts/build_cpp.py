"""Build script for HQT C++ engine.

Usage:
    python scripts/build_cpp.py              # Configure + build Release
    python scripts/build_cpp.py --debug      # Configure + build Debug
    python scripts/build_cpp.py --configure  # Configure only
    python scripts/build_cpp.py --build      # Build only (skip configure)
    python scripts/build_cpp.py --test       # Build + run tests
    python scripts/build_cpp.py --clean      # Remove build directory
    python scripts/build_cpp.py --install    # Build + copy module to project root
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BUILD_DIR = PROJECT_ROOT / "build"
VCPKG_TOOLCHAIN = Path("C:/vcpkg/scripts/buildsystems/vcpkg.cmake")
CMAKE_GENERATOR = "Visual Studio 18 2026"
CMAKE_ARCH = "x64"


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Execute a command, print it, and exit on failure."""
    print(f"\n>>> {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"FAILED with exit code {result.returncode}")
        sys.exit(result.returncode)
    return result


def _normalize_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").lower()


def _extract_cache_value(cache_text: str, key: str) -> str | None:
    prefix = f"{key}:INTERNAL="
    for line in cache_text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _repair_incompatible_cache(build_dir: Path, expected_generator: str) -> None:
    """Drop stale CMake cache when generator/path no longer matches."""
    cache = build_dir / "CMakeCache.txt"
    if not cache.exists():
        return

    text = cache.read_text(encoding="utf-8", errors="ignore")
    cache_dir = _extract_cache_value(text, "CMAKE_CACHEFILE_DIR")
    cache_gen = _extract_cache_value(text, "CMAKE_GENERATOR")
    expected_dir = _normalize_path(build_dir)

    mismatch = False
    if cache_dir:
        mismatch = mismatch or (_normalize_path(Path(cache_dir)) != expected_dir)
    if cache_gen:
        mismatch = mismatch or (cache_gen != expected_generator)

    if not mismatch:
        return

    cmake_files = build_dir / "CMakeFiles"
    if cmake_files.exists():
        shutil.rmtree(cmake_files, ignore_errors=True)
    cache.unlink(missing_ok=True)
    print(
        f"Repaired stale CMake cache in {build_dir} "
        f"(generator/path mismatch with {expected_generator})"
    )


def configure(build_type: str = "Release"):
    """Run CMake configure step."""
    BUILD_DIR.mkdir(exist_ok=True)
    _repair_incompatible_cache(BUILD_DIR, CMAKE_GENERATOR)

    cmd = [
        "cmake",
        "-B",
        str(BUILD_DIR),
        "-S",
        str(PROJECT_ROOT),
        f"-DCMAKE_TOOLCHAIN_FILE={VCPKG_TOOLCHAIN}",
        "-G",
        CMAKE_GENERATOR,
        "-A",
        CMAKE_ARCH,
        f"-DCMAKE_BUILD_TYPE={build_type}",
    ]
    run(cmd)


def build(build_type: str = "Release"):
    """Run CMake build step."""
    cmd = [
        "cmake",
        "--build",
        str(BUILD_DIR),
        "--config",
        build_type,
        "--parallel",
    ]
    run(cmd)


def test(build_type: str = "Release"):
    """Run CTest."""
    cmd = [
        "ctest",
        "--test-dir",
        str(BUILD_DIR),
        "-C",
        build_type,
        "--output-on-failure",
    ]
    run(cmd)


def install_module(build_type: str = "Release"):
    """Copy the built hqt_engine module to the project root for easy import."""
    # Find the built module (.pyd on Windows)
    for pattern in ["hqt_engine*.pyd", "hqt_engine*.so", "hqt_engine*.dll"]:
        for path in BUILD_DIR.rglob(pattern):
            dest = PROJECT_ROOT / path.name
            shutil.copy2(path, dest)
            print(f"Installed: {path.name} -> {dest}")
            return

    print("WARNING: Could not find built hqt_engine module")


def clean():
    """Remove build directory."""
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
        print(f"Removed {BUILD_DIR}")
    else:
        print("Build directory does not exist")


def main():
    """Parse arguments and run the requested build action."""
    parser = argparse.ArgumentParser(description="Build HQT C++ engine")
    parser.add_argument("--debug", action="store_true", help="Build in Debug mode")
    parser.add_argument("--configure", action="store_true", help="Configure only")
    parser.add_argument(
        "--build", action="store_true", help="Build only (skip configure)"
    )
    parser.add_argument("--test", action="store_true", help="Build and run tests")
    parser.add_argument("--clean", action="store_true", help="Remove build directory")
    parser.add_argument(
        "--install", action="store_true", help="Build and install module"
    )
    args = parser.parse_args()

    build_type = "Debug" if args.debug else "Release"

    if args.clean:
        clean()
        return

    if args.build:
        build(build_type)
    elif args.configure:
        configure(build_type)
    elif args.test:
        configure(build_type)
        build(build_type)
        test(build_type)
    elif args.install:
        configure(build_type)
        build(build_type)
        install_module(build_type)
    else:
        # Default: configure + build
        configure(build_type)
        build(build_type)


if __name__ == "__main__":
    main()
