from apps.logger import logger
import sys

def main():
    # Clear default handlers
    logger.remove()

    print("--- Formatting ---")

    print("\nSetting up Simple Format (output to stderr)...")
    logger.add(
        sys.stderr,
        format="{time} | {level} | {message}",
        level="INFO"
    )
    logger.info("This is a simple format message")
    logger.remove()


    print("\nSetting up Detailed Format...")
    logger.add(
        sys.stderr,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process}:{thread} | {name}:{function}:{line} - {message}",
        level="INFO"
    )
    logger.info("This is a detailed format message")
    logger.remove()

    print("\nSetting up Colored Console Format...")
    logger.add(
        sys.stderr,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.info("This is a colored format message")

if __name__ == "__main__":
    main()
