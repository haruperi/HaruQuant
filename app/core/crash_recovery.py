"""
Crash recovery mechanisms for the trading bot.
"""

import json
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

class BotState:
    """Manages bot state persistence and recovery."""
    
    def __init__(self, state_file: str = "data/bot_state.json"):
        """
        Initialize bot state manager.
        
        Args:
            state_file: Path to state file
        """
        self.state_file = Path(state_file)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state: Dict[str, Any] = self._load_state()
        
    def _load_state(self) -> Dict[str, Any]:
        """Load state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            return {
                'last_start_time': None,
                'last_stop_time': None,
                'crash_count': 0,
                'last_crash_time': None,
                'last_crash_reason': None,
                'last_known_state': None
            }
        except Exception as e:
            logger.error(f"Error loading state: {e}")
            return {}
            
    def save_state(self) -> None:
        """Save current state to file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state: {e}")
            
    def update_state(self, key: str, value: Any) -> None:
        """Update a specific state value."""
        self.state[key] = value
        self.save_state()
        
    def record_crash(self, reason: str) -> None:
        """Record a crash event."""
        self.state['crash_count'] = self.state.get('crash_count', 0) + 1
        self.state['last_crash_time'] = datetime.now().isoformat()
        self.state['last_crash_reason'] = reason
        self.save_state()
        
    def should_restart(self, max_crashes: int = 3, 
                      crash_window_hours: int = 24) -> bool:
        """
        Determine if bot should restart based on crash history.
        
        Args:
            max_crashes: Maximum allowed crashes in window
            crash_window_hours: Time window to consider crashes
            
        Returns:
            bool: True if bot should restart
        """
        if self.state.get('crash_count', 0) == 0:
            return True
            
        last_crash_time = self.state.get('last_crash_time')
        if not last_crash_time:
            return True
            
        last_crash = datetime.fromisoformat(last_crash_time)
        hours_since_crash = (datetime.now() - last_crash).total_seconds() / 3600
        
        if hours_since_crash > crash_window_hours:
            self.state['crash_count'] = 0
            self.save_state()
            return True
            
        return self.state['crash_count'] < max_crashes

class CrashRecovery:
    """Handles crash detection and recovery."""
    
    def __init__(self, bot_state: BotState):
        """
        Initialize crash recovery manager.
        
        Args:
            bot_state: BotState instance for state management
        """
        self.bot_state = bot_state
        self.original_sigint = None
        self.original_sigterm = None
        
    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.bot_state.update_state('last_stop_time', datetime.now().isoformat())
            sys.exit(0)
            
        self.original_sigint = signal.getsignal(signal.SIGINT)
        self.original_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def restore_signal_handlers(self) -> None:
        """Restore original signal handlers."""
        if self.original_sigint:
            signal.signal(signal.SIGINT, self.original_sigint)
        if self.original_sigterm:
            signal.signal(signal.SIGTERM, self.original_sigterm)
            
    def handle_crash(self, exception: Exception) -> None:
        """
        Handle a crash event.
        
        Args:
            exception: The exception that caused the crash
        """
        logger.exception("Bot crashed")
        self.bot_state.record_crash(str(exception))
        
    def should_restart(self) -> bool:
        """Determine if bot should restart after crash."""
        return self.bot_state.should_restart()
        
    def cleanup(self) -> None:
        """Clean up resources."""
        self.restore_signal_handlers()
        self.bot_state.update_state('last_stop_time', datetime.now().isoformat()) 