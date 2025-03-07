import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(log_file_name='HaruQuant.log', max_file_size=5*1024*1024, backup_count=3):
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

    # Check if the logger already has handlers to avoid duplication
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)   # Capture all levels from DEBUG to CRITICAL

        # Create a formatter to include details such as timestamp, logger name, log level, and message
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

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

# Disable propagation to prevent double logging
logger.propagate = False
    


# # Example logging calls (for reference)
# # General logging
# logger.debug("This is a debug message")
# logger.info("This is an info message")
# logger.warning("This is a warning message")
# logger.error("This is an error message")