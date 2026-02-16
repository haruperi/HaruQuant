"""Build the C++ Python bridge reliably from Python.

This script avoids common local issues by:
1) Using the standard Visual Studio build directory (default: build)
2) Building only the bridge target (hqt_engine)
3) Ensuring the built module is available at build/bridge/Release

Usage:
    python scripts/build_cpp_bridge.py
    python scripts/build_cpp_bridge.py --config Debug
    python scripts/build_cpp_bridge.py --run-usage
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUILD_DIR = PROJECT_ROOT / "build"
DEFAULT_GENERATOR = "Visual Studio 18 2026"
DEFAULT_ARCH = "x64"
DEFAULT_CONFIG = "Release"
DEFAULT_TOOLCHAIN = Path("C:/vcpkg/scripts/buildsystems/vcpkg.cmake")


def run(cmd: list[str]) -> None:
    print(f"\n>>> {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, cwd=str(PROJECT_ROOT))


def _normalize_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").lower()


def _repair_stale_cache(build_dir: Path) -> None:
    """Remove stale CMake cache when path/generator no longer matches."""
    cache = build_dir / "CMakeCache.txt"
    if not cache.exists():
        return

    text = cache.read_text(encoding="utf-8", errors="ignore")
    expected = _normalize_path(build_dir)

    # CMake stores the originating binary dir in cache internals.
    mismatch = False
    cache_dir = None
    cache_gen = None
    for line in text.splitlines():
        if line.startswith("CMAKE_CACHEFILE_DIR:INTERNAL="):
            cache_dir = line.split("=", 1)[1].strip()
        elif line.startswith("CMAKE_GENERATOR:INTERNAL="):
            cache_gen = line.split("=", 1)[1].strip()

    if cache_dir:
        mismatch = mismatch or (_normalize_path(Path(cache_dir)) != expected)
    if cache_gen:
        mismatch = mismatch or (cache_gen != DEFAULT_GENERATOR)

    if not mismatch:
        return

    cmake_files = build_dir / "CMakeFiles"
    if cmake_files.exists():
        shutil.rmtree(cmake_files, ignore_errors=True)
    cache.unlink(missing_ok=True)
    print(f"Repaired stale CMake cache in {build_dir}")


def configure(build_dir: Path, config: str, generator: str, arch: str, toolchain: Path) -> None:
    _repair_stale_cache(build_dir)
    cmd = [
        "cmake",
        "-B",
        str(build_dir),
        "-S",
        str(PROJECT_ROOT),
        f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
        "-G",
        generator,
        "-A",
        arch,
        f"-DCMAKE_BUILD_TYPE={config}",
    ]
    run(cmd)


def build(build_dir: Path, config: str, target: str) -> None:
    cmd = [
        "cmake",
        "--build",
        str(build_dir),
        "--config",
        config,
        "--parallel",
        "--target",
        target,
    ]
    run(cmd)


def copy_module(build_dir: Path, config: str) -> Path:
    src_dir = build_dir / "bridge" / config
    candidates = list(src_dir.glob("hqt_engine*.pyd"))
    if not candidates:
        raise FileNotFoundError(f"No hqt_engine module found in {src_dir}")

    src = candidates[0]
    dst_dir = PROJECT_ROOT / "build" / "bridge" / "Release"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name

    # When build_dir is already "build", src and dst are the same file.
    if src.resolve() == dst.resolve():
        print(f"Module ready: {dst}")
        return dst

    shutil.copy2(src, dst)
    print(f"Copied module: {src} -> {dst}")
    return dst


def run_usage_example() -> None:
    cmd = [sys.executable, "tests/usage/utils/usage_cpp_logger.py"]
    run(cmd)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build hqt_engine bridge from Python")
    parser.add_argument("--build-dir", type=Path, default=DEFAULT_BUILD_DIR)
    parser.add_argument("--config", default=DEFAULT_CONFIG, choices=["Debug", "Release"])
    parser.add_argument("--generator", default=DEFAULT_GENERATOR)
    parser.add_argument("--arch", default=DEFAULT_ARCH)
    parser.add_argument("--toolchain", type=Path, default=DEFAULT_TOOLCHAIN)
    parser.add_argument("--target", default="hqt_engine")
    parser.add_argument("--run-usage", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    configure(
        build_dir=args.build_dir,
        config=args.config,
        generator=args.generator,
        arch=args.arch,
        toolchain=args.toolchain,
    )
    build(build_dir=args.build_dir, config=args.config, target=args.target)
    copy_module(build_dir=args.build_dir, config=args.config)

    if args.run_usage:
        run_usage_example()


if __name__ == "__main__":
    main()
