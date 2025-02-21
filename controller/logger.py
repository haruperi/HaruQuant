import logging

# TODO: Setup logger using Python's built-in logging module
#   - The logger should store information about all important events and raised exceptions/errors during the operation of the bot.
#   - Example events to log include:
#       - MT5 Connection Server Failure
#       - Trade closed based on strategy
#       - Any other critical events or errors that may impact the bot's performance

# Create a logger instance
logger = logging.getLogger("bot_logger")
logger.setLevel(logging.DEBUG)  # Capture all levels from DEBUG to CRITICAL

# Create console handler for real-time output
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Create file handler to store logs persistently
file_handler = logging.FileHandler("bot.log")
file_handler.setLevel(logging.INFO)

# Define a formatter to include details such as timestamp, logger name, log level, and message
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Apply the formatter to both handlers
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Example logging calls (for reference)
# logger.error("MT5 Connection Server Failure")
# logger.info("Trade closed based on strategy")