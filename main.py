#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HaruTrader - Algorithmic Trading System for MetaTrader 5
Main entry point for the application.
"""

import sys
import logging
import argparse
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from app.core.bot import TradingBot
from app.core.system_monitor import SystemMonitor, SystemStatus
from app.config.settings import load_settings
from app.utils.logger import setup_root_logger, get_logger

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='HaruTrader - MT5 Trading Bot')
    parser.add_argument('--config', type=str, default='config.ini', help='Path to configuration file')
    parser.add_argument('--mode', type=str, choices=['live', 'backtest', 'optimize'], default='live', help='Operation mode')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--monitor-interval', type=float, default=60.0, help='System monitoring update interval in seconds')
    return parser.parse_args()

async def run_trading_system(config, mode, monitor_interval):
    """Run the trading system with monitoring."""
    logger = get_logger(__name__)
    
    # Initialize system monitor
    system_monitor = SystemMonitor(
        update_interval=monitor_interval,
        warning_thresholds={
            'cpu_percent': 80.0,
            'memory_percent': 80.0,
            'disk_percent': 80.0
        },
        critical_thresholds={
            'cpu_percent': 90.0,
            'memory_percent': 90.0,
            'disk_percent': 90.0
        }
    )
    
    # Initialize trading bot
    bot = TradingBot(config=config, mode=mode)
    
    try:
        # Start system monitoring
        await system_monitor.start()
        logger.info("System monitoring started")
        
        # Start trading bot
        bot.start()
        logger.info("Trading bot started")
        
        # Main monitoring loop
        while True:
            try:
                # Check system status
                status = system_monitor.get_system_status()
                if status == SystemStatus.CRITICAL:
                    logger.critical("System in critical state, initiating shutdown")
                    break
                elif status == SystemStatus.WARNING:
                    logger.warning("System in warning state")
                
                # Sleep for a short interval
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}", exc_info=True)
                await asyncio.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping gracefully...")
    except Exception as e:
        logger.exception("Fatal error occurred")
    finally:
        # Stop trading bot
        bot.stop()
        logger.info("Trading bot stopped")
        
        # Stop system monitoring
        await system_monitor.stop()
        logger.info("System monitoring stopped")

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
        
        # Run the trading system
        asyncio.run(run_trading_system(config, args.mode, args.monitor_interval))
        
        logger.info("Trading system stopped successfully")
        return 0
        
    except Exception as e:
        logger.exception("Error during system initialization")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 