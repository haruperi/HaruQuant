"""Usage examples for C++ error description and exception mapping.

Run:
    python backend/scripts/examples/utils/usage_error_description.py
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

BRIDGE_BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "bridge", "Release")
if BRIDGE_BUILD_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_BUILD_DIR)
if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(BRIDGE_BUILD_DIR)

VCPKG_BIN_DIR = os.path.join(PROJECT_ROOT, "build", "vcpkg_installed", "x64-windows", "bin")
if hasattr(os, "add_dll_directory") and os.path.isdir(VCPKG_BIN_DIR):
    os.add_dll_directory(VCPKG_BIN_DIR)

from backend.common import error_descriptions

def _header(name: str) -> None:
    print()
    print("=" * 72)
    print(name)
    print("=" * 72)


def f01_error_name() -> None:
    _header("f01_error_name")
    code = 10014  # invalid volume
    print(f"code={code}, name={error_descriptions.error_name(code)}")


def f02_error_payload() -> None:
    _header("f02_error_payload")
    code = 10019  # no money
    payload = error_descriptions.error_from_retcode(code)
    print(payload)


def f03_raise_exception_for_retcode() -> None:
    _header("f03_raise_exception_for_retcode")
    code = 10016  # invalid stops
    try:
        error_descriptions.raise_exception_for_retcode(code, "Example: stop loss is too close")
    except Exception as exc:
        print(type(exc).__name__)
        print(str(exc))


def f04_raise_exception_for_category() -> None:
    _header("f04_raise_exception_for_category")
    try:
        error_descriptions.raise_exception_for_category("risk", "Risk rule violated")
    except Exception as exc:
        print(type(exc).__name__)
        print(str(exc))


def run_all() -> None:
    f01_error_name()
    f02_error_payload()
    f03_raise_exception_for_retcode()
    f04_raise_exception_for_category()


if __name__ == "__main__":
    run_all()
