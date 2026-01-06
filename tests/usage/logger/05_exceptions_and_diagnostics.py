"""
Exception logging and diagnostics.

Covers:
- logger.exception()
- logger.opt(exception=...)
- backtrace and diagnose options on handlers
"""

import sys
from pathlib import Path
from typing import Any

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from apps.logger import Logger  # noqa: E402


def parse_number(value: Any) -> int:
    return int(value)


def main() -> None:
    print("=" * 60)
    print("Logger Example 05: Exceptions and Diagnostics")
    print("=" * 60)

    logger = Logger()
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="{level} | {message}",
        backtrace=True,
        diagnose=True,
    )

    try:
        _ = 1 / 0
    except ZeroDivisionError:
        logger.exception("Division failed")

    try:
        parse_number("not-a-number")
    except ValueError as exc:
        logger.opt(exception=exc).error("Parsing failed")

    logger.remove()
    print("=" * 60)


if __name__ == "__main__":
    main()
