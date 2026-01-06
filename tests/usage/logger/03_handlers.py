from apps.logger import logger
import sys

def main():
    print("--- Handlers ---")

    # Add flavored console output
    print("\nAdding colored console handler...")
    handler_id_console = logger.add(
        sys.stderr,
        level="INFO",
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    logger.info("This logic goes to stderr with color")

    # Add file handler
    print("\nAdding file handler...")
    handler_id_file = logger.add(
        "logs/app_usage.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="1 MB",
        retention="10 days",
        compression="zip"
    )
    logger.debug("This message goes to the file")

    # Custom handler function
    print("\nAdding callable handler...")
    def send_to_monitoring(message):
        # We use print here just to demonstrate it's working
        print(f"MONITORING_MOCK: {message}")

    handler_id_callable = logger.add(
        send_to_monitoring,
        level="ERROR",
        format="{time} | {level} | {message}"
    )
    logger.error("This error goes to monitoring")

    print("\n--- Removing Handlers ---")
    
    # Remove specific handler
    logger.remove(handler_id_console)
    logger.info("This will NOT show in the custom console handler (removed) but WILL show in file if level permits")

    # Remove all handlers
    logger.remove()
    logger.info("This will not be logged anywhere (all handlers removed)")

if __name__ == "__main__":
    main()
