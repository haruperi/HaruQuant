"""
Custom levels, decorators, and opt().

Covers:
- add_level() custom log levels
- @logger.catch decorator
- opt(depth=...) for caller attribution
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from apps.logger import Logger  # noqa: E402


def main() -> None:
    print("=" * 60)
    print("Logger Example 08: Custom Levels and Decorators")
    print("=" * 60)

    logger = Logger()
    logger.add(sys.stdout, level="TRACE", format="{level: <8} | {message}")

    logger.add_level("NOTICE", 22, color="blue", icon="!")
    # Use log() for dynamic levels to avoid linting errors about missing members
    logger.log("NOTICE", "Notice message")

    @logger.catch(level="ERROR", message="Failed to process order")
    def process_order(order_id: int) -> bool:
        if order_id < 0:
            raise ValueError("order_id must be positive")
        return True

    process_order(-1)

    def heavy_operation(n: int) -> int:
        logger.opt(depth=1).info("Logged from caller via opt(depth=1)")
        return n * 2

    def caller() -> None:
        heavy_operation(5)

    caller()

    logger.remove()
    print("=" * 60)


if __name__ == "__main__":
    main()
