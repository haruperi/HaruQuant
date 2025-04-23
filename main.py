#!/usr/bin/env python
"""
HaruQuant Trading Bot - Main Entry Point
"""

import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/haruquant.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point for the HaruQuant trading bot."""
    try:
        # Load environment variables
        load_dotenv()
        
        # Create necessary directories
        Path('logs').mkdir(exist_ok=True)
        Path('data/historical').mkdir(parents=True, exist_ok=True)
        Path('data/backtest_results').mkdir(parents=True, exist_ok=True)
        Path('data/optimization_results').mkdir(parents=True, exist_ok=True)
        
        logger.info("Starting HaruQuant Trading Bot...")
        
        # TODO: Initialize and run the trading bot
        # from app.core.bot import TradingBot
        # bot = TradingBot()
        # bot.run()
        
        logger.info("HaruQuant Trading Bot started successfully")
        
    except Exception as e:
        logger.exception("Error starting HaruQuant Trading Bot")
        raise

if __name__ == "__main__":
    main() 