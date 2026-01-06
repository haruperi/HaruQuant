"""
Async logging and serialization.

Covers:
- enqueue=True async handlers
- max_queue_size and overflow strategy
- serialize=True for JSON output
"""

import sys
import time
from pathlib import Path
from typing import Any

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from apps.logger import Logger  # noqa: E402


def main() -> None:
    print("=" * 60)
    print("Logger Example 07: Async and Serialization")
    print("=" * 60)

    logger = Logger()
    captured = []

    def capture(message: Any) -> None:
        captured.append(message)

    logger.add(
        capture,
        level="INFO",
        format="{message}",
        serialize=True,
        enqueue=True,
        max_queue_size=100,
        overflow_strategy="block",
    )

    logger.info("Async serialized record", event="startup", attempt=1)

    file_id = logger.add(
        "logs/logger_async.log",
        level="INFO",
        format="{time:HH:mm:ss} | {message}",
        enqueue=True,
    )

    for i in range(5):
        logger.info("Async file message {}", i)

    time.sleep(0.2)

    if captured:
        print("Captured JSON:", captured[0])

    logger.remove(file_id)
    logger.remove()
    print("=" * 60)


if __name__ == "__main__":
    main()
