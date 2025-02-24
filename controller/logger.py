import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(log_file_name='bot.log', max_file_size=5*1024*1024, backup_count=3):
    """
    Setup and configure the logger for the bot.

    Args:
    log_file_path (str): Path to the log file.
    max_file_size (int): Maximum size of each log file in bytes.
    backup_count (int): Number of backup log files to keep.

    Returns:
    logging.Logger: Configured logger instance.
    """

    # Get the path to the root directory (one level up from the current file)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Create the logs directory in the root folder
    logs_dir = os.path.join(root_dir, 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Construct the full path for the log file
    log_file_path = os.path.join(logs_dir, log_file_name)

    # Create logger
    logger = logging.getLogger("bot_logger")
    logger.setLevel(logging.DEBUG)      # Capture all levels from DEBUG to CRITICAL

    # Create a formatter to include details such as timestamp, logger name, log level, and message
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create console handler for real-time output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Create rotating file handler to store logs persistently
    file_handler = RotatingFileHandler(log_file_path, maxBytes=max_file_size, backupCount=backup_count)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# Create the logger instance
logger = setup_logger()

# Custom log methods for specific events
def log_mt5_connection_failure(error_message):
    logger.error(f"MT5 Connection Server Failure: {error_message}")

def log_trade_closed(strategy, trade_details):
    logger.info(f"Trade closed based on strategy '{strategy}': {trade_details}")

def log_critical_event(event_type, details):
    logger.critical(f"Critical Event - {event_type}: {details}")


# # Example logging calls (for reference)
# # Test logging
# log_mt5_connection_failure("Unable to establish connection to MT5 server")
# log_trade_closed("Moving Average Crossover", {"symbol": "EURUSD", "profit": 50})
# log_critical_event("Data Feed Interruption", "Lost connection to price feed for 5 minutes")
#
# # General logging
# logger.debug("This is a debug message")
# logger.info("This is an info message")
# logger.warning("This is a warning message")
# logger.error("This is an error message")