"""
Filtering and module control.

Covers:
- handler filters (callable, LevelFilter, ModuleFilter)
- disable() and enable() for module control
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from apps.logger import Logger  # noqa: E402
from apps.logger.filter import LevelFilter, ModuleFilter  # noqa: E402

if TYPE_CHECKING:
    from apps.logger.record import LogRecord


def main() -> None:
    print("=" * 60)
    print("Logger Example 04: Filters and Module Control")
    print("=" * 60)

    logger = Logger()

    level_filter = LevelFilter(min_level=30)

    def audit_filter(record: "LogRecord") -> bool:
        return record.extra.get("type") == "audit"

    def ignore_debug_filter(record: "LogRecord") -> bool:
        return (
            record.level.no > 10
        )  # Assuming DEBUG is 10, this filter allows anything above DEBUG

    logger.add(
        sys.stdout,
        level="TRACE",
        filter=level_filter,
        format="LEVEL FILTER | {level} | {message}",
    )
    logger.add(
        sys.stdout,
        level="TRACE",
        filter=audit_filter,
        format="AUDIT FILTER | {level} | {message}",
    )
    logger.add(
        sys.stdout,
        level="TRACE",
        filter=ignore_debug_filter,
        format="CUSTOM FILTER | {level} | {message}",
    )

    logger.info("Info should not pass level filter")
    logger.warning("Warning passes level filter")
    logger.bind(type="audit").info("Audit event passes audit filter")
    logger.error("Error passes level filter")

    module_logger = Logger()
    module_logger.add(
        sys.stdout,
        level="INFO",
        filter=ModuleFilter(modules=["__main__"]),
        format="MODULE FILTER | {module} | {message}",
    )

    module_logger.info("Module filter allows __main__")
    module_logger.disable("__main__")
    module_logger.info("This should be suppressed")
    module_logger.enable("__main__")
    module_logger.info("Logging enabled again")

    logger.remove()
    module_logger.remove()
    print("=" * 60)


if __name__ == "__main__":
    main()
