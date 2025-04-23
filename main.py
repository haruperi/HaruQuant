#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HaruTrader - Algorithmic Trading System for MetaTrader 5
Main entry point for the application.
"""

import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv
from app.core.bot import TradingBot
from app.config.settings import load_settings
from app.utils.logger import setup_root_logger, get_logger

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='HaruTrader - MT5 Trading Bot')
    parser.add_argument('--config', type=str, default='config.ini', help='Path to configuration file')
    parser.add_argument('--mode', type=str, choices=['live', 'backtest', 'optimize'], default='live', help='Operation mode')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    return parser.parse_args()

def main():
    """Application entry point."""
    try:
        # Create necessary directories
        Path('logs').mkdir(exist_ok=True)
        Path('data/historical').mkdir(parents=True, exist_ok=True)
        Path('data/backtest_results').mkdir(parents=True, exist_ok=True)
        Path('data/optimization_results').mkdir(parents=True, exist_ok=True)

        # Parse command line arguments
        args = parse_arguments()
        
        # Load environment variables
        load_dotenv()
        
        # Setup logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        setup_root_logger(log_level=log_level)
        logger = get_logger(__name__)
        
        logger.info("Starting HaruTrader Trading Bot...")
        
        # Load configuration
        config = load_settings(args.config)
        logger.info(f"Loaded configuration from {args.config}")
        logger.info(f"Running in {args.mode} mode")
        
        # Initialize and run the trading bot
        bot = TradingBot(config=config, mode=args.mode)
        
        try:
            bot.start()
        except KeyboardInterrupt:
            logger.info("Received shutdown signal, stopping gracefully...")
            bot.stop()
        except Exception as e:
            logger.exception("Fatal error occurred")
            bot.stop()
            return 1
            
        logger.info("Trading bot stopped successfully")
        return 0
        
    except Exception as e:
        logger.exception("Error during bot initialization")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 