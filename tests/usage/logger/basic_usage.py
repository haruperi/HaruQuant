from apps.logger import logger

def main():
    print("--- Basic Usage ---")
    
    # Simple logging
    logger.info("Application started")
    logger.success("Operation completed successfully")
    logger.warning("Low disk space")
    logger.error("Failed to connect to database")
    logger.critical("System shutdown initiated")

    print("\n--- With Arguments ---")
    
    # Positional arguments
    logger.info("User {} logged in", "john_doe")
    logger.info("Processing {} items in {} seconds", 100, 2.5)

    # Named arguments
    logger.info("User {user} logged in from {city}", user="john_doe", city="NYC")
    logger.error("Failed to process order {order_id}", order_id=12345)

    print("\n--- With Context ---")
    
    # Add extra context
    logger.info("Trade executed", symbol="EURUSD", price=1.0950, volume=1.0)
    logger.error("Order failed", order_id=123, reason="Insufficient margin")

if __name__ == "__main__":
    main()
