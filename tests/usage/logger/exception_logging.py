from apps.logger import logger
import sys

# Mock function for example
def process_order(order_id, user_id=None):
    raise ValueError("Order processing failed due to invalid state")

def risky_operation():
    raise RuntimeError("Something risky went wrong")

def main():
    print("--- Exception Logging ---")

    print("\nBasic Exception Logging:")
    try:
        result = 10 / 0
    except Exception as e:
        logger.exception("Division error occurred")

    print("\nException with Context:")
    try:
        process_order(order_id=123)
    except Exception as e:
        logger.exception("Failed to process order", order_id=123, user_id=456)

    print("\nManual Exception Logging:")
    try:
        risky_operation()
    except Exception:
        exc_info = sys.exc_info()
        logger.error("Operation failed", exc_info=exc_info)

if __name__ == "__main__":
    main()
