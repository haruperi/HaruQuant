"""
Event handling system for the trading bot
"""

import logging
from typing import Callable, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class Event:
    """Base event class."""
    timestamp: datetime
    type: str
    data: Any

class EventSystem:
    """Event handling system for the trading bot."""
    
    def __init__(self):
        """Initialize the event system."""
        self._handlers: Dict[str, List[Callable]] = {}
        
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The function to call when the event occurs
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed to event type: {event_type}")
        
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from an event type.
        
        Args:
            event_type: The type of event to unsubscribe from
            handler: The function to remove from the handlers
        """
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
            logger.debug(f"Unsubscribed from event type: {event_type}")
            
    def emit(self, event_type: str, data: Any = None) -> None:
        """Emit an event.
        
        Args:
            event_type: The type of event to emit
            data: The data associated with the event
        """
        event = Event(
            timestamp=datetime.now(),
            type=event_type,
            data=data
        )
        
        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.exception(f"Error handling event {event_type}")
                    
    def get_handlers(self, event_type: str) -> List[Callable]:
        """Get all handlers for an event type.
        
        Args:
            event_type: The type of event to get handlers for
            
        Returns:
            List of handlers for the event type
        """
        return self._handlers.get(event_type, []) 