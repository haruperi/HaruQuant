"""
WebSocket Log Handler for Backtest Streaming.

Custom logging handler that captures log messages and broadcasts
them to connected WebSocket clients in real-time.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional


class WebSocketLogHandler(logging.Handler):
    """
    Custom log handler that broadcasts log messages via WebSocket.

    Captures log messages during backtest execution and sends them
    to all connected WebSocket clients for real-time display.
    """

    def __init__(self, backtest_id: int, log_manager, level=logging.INFO):
        """
        Initialize the WebSocket log handler.

        Args:
            backtest_id: ID of the backtest to broadcast logs for
            log_manager: BacktestLogManager instance for broadcasting
            level: Minimum log level to capture (default: INFO)
        """
        super().__init__(level)
        self.backtest_id = backtest_id
        self.log_manager = log_manager
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def emit(self, record: logging.LogRecord):
        """
        Emit a log record by broadcasting it via WebSocket.

        Args:
            record: Log record to broadcast
        """
        try:
            # Only broadcast if there are connected clients
            if not self.log_manager.has_connections(self.backtest_id):
                return

            # Format the log message
            message = {
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "message": self.format(record),
                "source": record.name,
                "backtest_id": self.backtest_id,
            }

            # Get or create event loop
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # No running loop, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Schedule the broadcast
            asyncio.create_task(self.log_manager.broadcast(self.backtest_id, message))

        except Exception as e:
            # Don't let logging errors break the backtest
            print(f"Error in WebSocketLogHandler: {e}")
