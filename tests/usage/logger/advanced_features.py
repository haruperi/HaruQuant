from apps.logger import logger

def main():
    print("--- Advanced Features ---")

    print("\nContext Manager example:")
    # Temporarily change options
    with logger.contextualize(user_id=123, session_id="abc"):
        logger.info("User action")  # Includes user_id and session_id
        logger.info("Another action")  # Also includes context
    logger.info("Outside context") # Does not include context

    print("\nOptions example:")
    # Skip frame inspection (faster)
    logger.opt(depth=0).info("Fast log message (depth=0)")

    # Include exception info (simulated here with log call, normally used in except block)
    # logger.opt(exception=True).error("Error occurred") 

    # Custom depth for frame inspection
    logger.opt(depth=2).info("Message from caller's caller (depth=2)")

    print("\nBinding example:")
    # Create bound logger
    user_logger = logger.bind(user_id=123, username="john_doe")

    # All logs from this logger include context
    user_logger.info("User logged in")  # Includes user_id and username
    user_logger.info("User logged out")  # Also includes context

    logger.info("Unbound logger message")

if __name__ == "__main__":
    main()
