from apps.logger import logger
import sys

# Mock multiprocessing for "Multi-Process Logging"
from multiprocessing import Process

def common_application_logging():
    print("\n--- Application Logging Pattern ---")
    logger.remove() # Clear
    
    # Console output (INFO and above)
    logger.add(
        sys.stderr,
        level="INFO",
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    # File output (DEBUG and above)
    logger.add(
        "logs/app_pattern.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="500 MB",
        retention="30 days",
        compression="zip"
    )
    
    # Error file (ERROR and above)
    logger.add(
        "logs/errors_pattern.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
        rotation="100 MB",
        retention="90 days"
    )
    
    logger.info("Application started (Pattern)")
    logger.debug("Debug info for file only")
    logger.error("Error for console and both files")

def trading_strategy_logging():
    print("\n--- Trading Strategy Logging Pattern ---")
    
    # Create strategy-specific logger
    strategy_logger = logger.bind(strategy="MA_Crossover", version="1.0.0")
    
    # Log strategy events
    strategy_logger.info("Strategy initialized", symbol="EURUSD", timeframe="H1")
    strategy_logger.debug("Calculating indicators", fast_ma=12, slow_ma=26)
    strategy_logger.success("Buy signal generated", price=1.0950, confidence=0.85)
    strategy_logger.warning("High volatility detected", atr=0.0015)
    strategy_logger.error("Order execution failed", order_id=123, reason="Insufficient margin")

def backtest_logging():
    print("\n--- Backtest Logging Pattern ---")
    logger.remove()
    logger.add(
        "logs/backtest_{time:YYYY-MM-DD}.log",
        level="INFO",
        format="{time:HH:mm:ss} | {level: <8} | {message}",
        rotation="1 day"
    )
    
    # Log backtest progress
    logger.info("Backtest started", symbol="EURUSD", start="2024-01-01", end="2024-12-31")
    logger.info("Processing data", bars=10000, progress=0.25)
    logger.success("Backtest completed", total_trades=150, win_rate=0.62, profit=2500)

def error_monitoring():
    print("\n--- Error Monitoring Pattern ---")
    def send_to_slack(message):
        print(f"[MOCK SLACK] {message}")
    
    # Add Slack handler for critical errors
    logger.add(
        send_to_slack,
        level="CRITICAL",
        format="{time} | {level} | {message}"
    )
    
    # Critical errors will be sent to Slack
    logger.critical("Database connection lost")
    logger.critical("System out of memory")

def worker(worker_id):
    # Re-import logger inside process if needed, or rely on fork safety if on POSIX
    # Windows needs care with multiprocessing.
    # Here we just demonstrate the binding logic.
    worker_logger = logger.bind(worker_id=worker_id)
    worker_logger.info("Worker started")
    # Do work...
    worker_logger.info("Worker finished")

def multi_process_logging():
    print("\n--- Multi-Process Logging Pattern ---")
    # Note: On Windows, without 'if __name__ == "__main__":' guard and proper spawn,
    # this might fail in a script. We will skip the actual spawn for this usage example checks
    # and just show setup.
    
    print("Configuring logger for multiprocessing (enqueue=True)...")
    logger.add("logs/workers.log", enqueue=True)  # Thread-safe
    
    print("Starting workers (Simulated loop)...")
    # processes = [Process(target=worker, args=(i,)) for i in range(4)]
    # for p in processes: p.start()
    # for p in processes: p.join()
    for i in range(2):
        worker(i) # Sequential simulation for usage test without spawn overhead

def main():
    common_application_logging()
    trading_strategy_logging()
    backtest_logging()
    error_monitoring()
    multi_process_logging()

if __name__ == "__main__":
    main()
