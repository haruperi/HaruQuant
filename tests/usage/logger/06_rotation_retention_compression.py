"""
Rotation, retention, and compression.

Covers:
- size-based rotation
- retention policy
- compression of rotated files
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from apps.logger import Logger  # noqa: E402


def main() -> None:
    print("=" * 60)
    print("Logger Example 06: Rotation and Retention")
    print("=" * 60)

    logger = Logger()
    handler_id = logger.add(
        "logs/logger_rotating.log",
        level="INFO",
        format="{time:HH:mm:ss} | {message}",
        rotation="1 KB",
        retention=3,
        compression="gz",
    )

    for i in range(200):
        logger.info("Rotating message {}", i)

    logger.remove(handler_id)
    print("=" * 60)


if __name__ == "__main__":
    main()
