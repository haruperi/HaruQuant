from apps.logger import logger

def main():
    print("--- Log Levels ---")
    
    # Different log levels
    logger.trace("Entering function calculate_profit()")
    logger.debug("Variable state: balance={}, equity={}", 10000, 10500)
    logger.info("Starting backtest for EURUSD")
    logger.success("Backtest completed successfully")
    logger.warning("High CPU usage detected: 85%")
    logger.error("Failed to fetch market data")
    logger.critical("Database connection lost")

    print("\n--- Custom Log Level ---")
    
    # Log at specific level
    logger.log("INFO", "This is an info message")
    logger.log(20, "This is also an info message")
    logger.log("SUCCESS", "Custom success message")

if __name__ == "__main__":
    main()
