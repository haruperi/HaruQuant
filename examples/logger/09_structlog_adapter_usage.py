import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.utils.logger import logger


def main():
    print("--- Structlog Adapter Usage ---")

    received = []
    handler_id = logger.add(received.append, level="INFO", raw=True)

    try:
        bound = logger.bind(component="usage_demo", run_id="demo-001")

        bound.info("Starting demo run")
        bound.success("Connected to provider")
        bound.warning("Spread widening detected")
        bound.error(
            "Auth failed password=secret123 token=abcd",
            extra={"api_key": "never-log-this", "safe": "ok"},
        )

        print(f"Captured records: {len(received)}")
        if received:
            last = received[-1]
            print(f"Last level: {last.level.name}")
            print(f"Last message: {last.message}")
            print(f"Last extra: {last.extra}")
    finally:
        logger.remove(handler_id)


if __name__ == "__main__":
    main()

