from apps.logger import logger
import sys

def development_configuration():
    print("--- Development Configuration ---")
    logger.remove()
    
    # Verbose console output
    logger.add(
        sys.stderr,
        level="DEBUG",
        colorize=True,
        format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}:{function}:{line}</cyan> - <level>{message}</level>"
    )
    
    # Detailed file log
    logger.add(
        "logs/dev.log",
        level="TRACE",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process}:{thread} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="3 days"
    )
    
    logger.trace("Trace message (Dev)")
    logger.debug("Debug message (Dev)")

def production_configuration():
    print("\n--- Production Configuration ---")
    logger.remove()
    
    # Minimal console output
    logger.add(
        sys.stderr,
        level="WARNING",
        format="{time:HH:mm:ss} | {level: <8} | {message}"
    )
    
    # Application log
    logger.add(
        "logs/app_prod.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        rotation="500 MB",
        retention="30 days",
        compression="zip",
        enqueue=True  # Thread-safe
    )
    
    # Error log
    logger.add(
        "logs/error_prod.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
        rotation="100 MB",
        retention="90 days",
        compression="zip"
    )
    
    logger.info("Informational message (Prod)") # Shows in app_prod.log
    logger.debug("Debug message (Prod)") # Ignored
    logger.warning("Warning message (Prod)") # Shows in console and app_prod.log
    logger.error("Error message (Prod)") # Shows in console, app_prod.log, and error_prod.log

def main():
    development_configuration()
    production_configuration()

    # Reset default for other scripts if run sequentially in same process (not applicable here but good practice)
    logger.remove()
    logger.add(sys.stderr)

if __name__ == "__main__":
    main()
