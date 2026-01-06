"""
Context binding.

Covers:
- bind() for permanent context
- contextualize() for temporary context
- extra merging across contexts
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from apps.logger import Logger  # noqa: E402


def main() -> None:
    print("=" * 60)
    print("Logger Example 03: Context Binding")
    print("=" * 60)

    logger = Logger()
    logger.add(
        sys.stdout,
        level="INFO",
        format="{level} | user={extra.user} request={extra.request_id} | {message}",
    )

    user_logger = logger.bind(user="alice")

    user_logger.info("User session started", request_id="req-100")

    with logger.contextualize(request_id="req-200"):
        user_logger.info("Processing request")
        user_logger.info("Request complete")

    user_logger.info("Request context cleared", request_id="req-300")

    logger.remove()
    print("=" * 60)


if __name__ == "__main__":
    main()
