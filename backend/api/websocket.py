"""
WebSocket Manager for Real-time Updates.

from backend.common.logger import logger
Manages WebSocket connections for:
- Backtest logs streaming
- Live trading updates (signals, positions, status, logs)
"""

import asyncio
from collections import deque
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket


async def _send_json_to_connections(connections: List[WebSocket], message: dict):
    disconnected = []
    for websocket in connections:
        try:
            await websocket.send_json(message)
        except Exception:
            disconnected.append(websocket)
    return disconnected


class BacktestLogManager:
    """
    Manages WebSocket connections for backtest log streaming.

    Allows multiple clients to connect to a backtest and receive
    real-time log updates during execution.
    """

    def __init__(self):
        """Initialize the log manager with empty connections."""
        # Map of backtest_id -> list of connected WebSockets
        self.connections: Dict[int, List[WebSocket]] = {}
        # Map of backtest_id -> deque of buffered log messages
        self.log_buffers: Dict[int, deque] = {}
        # Maximum number of logs to buffer per backtest
        self.max_buffer_size = 10000
        self._lock = asyncio.Lock()

    async def connect(self, backtest_id: int, websocket: WebSocket):
        """
        Add a WebSocket connection for a backtest and send buffered logs.

        Args:
            backtest_id: ID of the backtest
            websocket: WebSocket connection to add
        """
        await websocket.accept()

        # Initialize buffered_logs outside the lock
        buffered_logs = []

        async with self._lock:
            if backtest_id not in self.connections:
                self.connections[backtest_id] = []
            self.connections[backtest_id].append(websocket)

            # Send all buffered logs to the newly connected client
            if backtest_id in self.log_buffers:
                buffered_logs = list(self.log_buffers[backtest_id])

        # Send buffered logs outside the lock to avoid blocking
        for log_message in buffered_logs:
            try:
                await websocket.send_json(log_message)
            except Exception:
                # If sending fails, remove the connection
                await self.disconnect(backtest_id, websocket)
                break

    async def disconnect(self, backtest_id: int, websocket: WebSocket):
        """
        Remove a WebSocket connection for a backtest.

        Args:
            backtest_id: ID of the backtest
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            if backtest_id in self.connections:
                if websocket in self.connections[backtest_id]:
                    self.connections[backtest_id].remove(websocket)

                # Clean up empty lists
                if not self.connections[backtest_id]:
                    del self.connections[backtest_id]

    async def broadcast(self, backtest_id: int, message: dict):
        """
        Broadcast a message to all connected clients and buffer it for future connections.

        Args:
            backtest_id: ID of the backtest
            message: Message to broadcast (will be sent as JSON)
        """
        async with self._lock:
            # Always buffer the message for late-connecting clients
            if backtest_id not in self.log_buffers:
                self.log_buffers[backtest_id] = deque(maxlen=self.max_buffer_size)
            self.log_buffers[backtest_id].append(message)

            # Get connections if any exist
            connections = (
                self.connections[backtest_id].copy()
                if backtest_id in self.connections
                else []
            )

        # Send to all active connections (outside lock to avoid blocking)
        if connections:
            disconnected = await _send_json_to_connections(connections, message)
            if disconnected:
                async with self._lock:
                    if backtest_id in self.connections:
                        for ws in disconnected:
                            if ws in self.connections[backtest_id]:
                                self.connections[backtest_id].remove(ws)

                        # Clean up empty lists
                        if not self.connections[backtest_id]:
                            del self.connections[backtest_id]

    def has_connections(self, backtest_id: int) -> bool:
        """
        Check if there are any active connections for a backtest.

        Args:
            backtest_id: ID of the backtest

        Returns:
            True if there are active connections, False otherwise
        """
        return (
            backtest_id in self.connections and len(self.connections[backtest_id]) > 0
        )

    async def clear_buffer(self, backtest_id: int):
        """
        Clear the log buffer for a completed backtest.

        Args:
            backtest_id: ID of the backtest
        """
        async with self._lock:
            if backtest_id in self.log_buffers:
                del self.log_buffers[backtest_id]


# Global instance
backtest_log_manager = BacktestLogManager()


class LiveTradingManager:
    """
    Manages WebSocket connections for live trading updates.

    Allows multiple clients to connect to a live trading session and receive
    real-time updates for signals, positions, status changes, and logs.
    """

    def __init__(self):
        """Initialize the live trading manager with empty connections."""
        # Map of session_id -> set of connected WebSockets
        self.connections: Dict[int, Set[WebSocket]] = {}
        # Map of session_id -> dict of channel subscriptions
        # {session_id: {websocket: set(channels)}}
        self.subscriptions: Dict[int, Dict[WebSocket, Set[str]]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: int, websocket: WebSocket):
        """
        Add a WebSocket connection for a live trading session.

        Args:
            session_id: ID of the trading session
            websocket: WebSocket connection to add
        """
        await websocket.accept()

        async with self._lock:
            if session_id not in self.connections:
                self.connections[session_id] = set()
                self.subscriptions[session_id] = {}

            self.connections[session_id].add(websocket)
            # Default subscription to all channels
            self.subscriptions[session_id][websocket] = {
                "signals",
                "positions",
                "status",
                "logs",
            }

    async def disconnect(self, session_id: int, websocket: WebSocket):
        """
        Remove a WebSocket connection for a trading session.

        Args:
            session_id: ID of the trading session
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            if session_id in self.connections:
                if websocket in self.connections[session_id]:
                    self.connections[session_id].remove(websocket)

                if websocket in self.subscriptions[session_id]:
                    del self.subscriptions[session_id][websocket]

                # Clean up empty sets/dicts
                if not self.connections[session_id]:
                    del self.connections[session_id]
                    del self.subscriptions[session_id]

    async def subscribe(
        self, session_id: int, websocket: WebSocket, channels: List[str]
    ):
        """
        Subscribe a WebSocket to specific channels.

        Args:
            session_id: ID of the trading session
            websocket: WebSocket connection
            channels: List of channels to subscribe to
        """
        async with self._lock:
            if (
                session_id in self.subscriptions
                and websocket in self.subscriptions[session_id]
            ):
                self.subscriptions[session_id][websocket] = set(channels)

    async def _get_subscribed_connections(
        self, session_id: int, channel: str
    ) -> List[WebSocket]:
        async with self._lock:
            if session_id not in self.connections:
                return []

            subscribed = []
            for ws in self.connections[session_id]:
                if (
                    ws in self.subscriptions[session_id]
                    and channel in self.subscriptions[session_id][ws]
                ):
                    subscribed.append(ws)
        return subscribed

    async def _remove_disconnected(
        self, session_id: int, disconnected: List[WebSocket]
    ):
        async with self._lock:
            if session_id in self.connections:
                for ws in disconnected:
                    if ws in self.connections[session_id]:
                        self.connections[session_id].remove(ws)
                    if ws in self.subscriptions[session_id]:
                        del self.subscriptions[session_id][ws]

                if not self.connections[session_id]:
                    del self.connections[session_id]
                    del self.subscriptions[session_id]

    async def broadcast(
        self, session_id: int, channel: str, message: dict, include_type: bool = True
    ):
        """
        Broadcast a message to all subscribed clients on a specific channel.

        Args:
            session_id: ID of the trading session
            channel: Channel name (signals, positions, status, logs)
            message: Message to broadcast (will be sent as JSON)
            include_type: Whether to include "type" field (channel name) in message
        """
        subscribed_connections = await self._get_subscribed_connections(
            session_id, channel
        )
        if not subscribed_connections:
            return

        # Prepare message
        if include_type:
            message_to_send = {"type": channel, "session_id": session_id, **message}
        else:
            message_to_send = message

        # Send to all subscribed connections (outside lock to avoid blocking)
        disconnected = await _send_json_to_connections(
            subscribed_connections, message_to_send
        )
        if disconnected:
            await self._remove_disconnected(session_id, disconnected)

    def has_connections(self, session_id: int, channel: Optional[str] = None) -> bool:
        """
        Check if there are any active connections for a session.

        Args:
            session_id: ID of the trading session
            channel: Optional channel name to check for subscribers

        Returns:
            True if there are active connections, False otherwise
        """
        if channel is None:
            return bool(self.connections.get(session_id))

        subscriptions = self.subscriptions.get(session_id, {})
        return any(channel in channels for channels in subscriptions.values())

    async def send_signal_detected(self, session_id: int, signal: dict):
        """
        Send signal_detected event to subscribed clients.

        Args:
            session_id: ID of the trading session
            signal: Signal data
        """
        await self.broadcast(session_id, "signals", {"data": signal})

    async def send_signal_approved(self, session_id: int, signal: dict):
        """
        Send signal_approved event to subscribed clients.

        Args:
            session_id: ID of the trading session
            signal: Signal data
        """
        await self.broadcast(
            session_id,
            "signals",
            {"type": "signal_approved", "data": signal},
            include_type=False,
        )

    async def send_signal_rejected(self, session_id: int, signal: dict, reason: str):
        """
        Send signal_rejected event to subscribed clients.

        Args:
            session_id: ID of the trading session
            signal: Signal data
            reason: Rejection reason
        """
        await self.broadcast(
            session_id,
            "signals",
            {"type": "signal_rejected", "data": signal, "reason": reason},
            include_type=False,
        )

    async def send_position_opened(self, session_id: int, position: dict):
        """
        Send position_opened event to subscribed clients.

        Args:
            session_id: ID of the trading session
            position: Position data
        """
        await self.broadcast(
            session_id,
            "positions",
            {"type": "position_opened", "data": position},
            include_type=False,
        )

    async def send_position_updated(self, session_id: int, position: dict):
        """
        Send position_updated event to subscribed clients.

        Args:
            session_id: ID of the trading session
            position: Position data
        """
        await self.broadcast(
            session_id,
            "positions",
            {"type": "position_updated", "data": position},
            include_type=False,
        )

    async def send_position_closed(self, session_id: int, position: dict, reason: str):
        """
        Send position_closed event to subscribed clients.

        Args:
            session_id: ID of the trading session
            position: Position data
            reason: Close reason
        """
        await self.broadcast(
            session_id,
            "positions",
            {
                "type": "position_closed",
                "data": position,
                "reason": reason,
            },
            include_type=False,
        )

    async def send_status_update(self, session_id: int, status: dict):
        """
        Send status_update event to subscribed clients.

        Args:
            session_id: ID of the trading session
            status: Status data
        """
        await self.broadcast(session_id, "status", {"data": status})

    async def send_log_message(
        self,
        session_id: int,
        level: str,
        category: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Send log_message event to subscribed clients.

        Args:
            session_id: ID of the trading session
            level: Log level (info, warning, error, critical)
            category: Log category (signal, risk, execution, trade_mgmt, system)
            message: Log message
            details: Optional additional details
        """
        await self.broadcast(
            session_id,
            "logs",
            {
                "level": level,
                "category": category,
                "message": message,
                "details": details,
                "timestamp": asyncio.get_event_loop().time(),
            },
        )


# Global instance
live_trading_manager = LiveTradingManager()


class OptimizationProgressManager:
    """
    Manages WebSocket connections for optimization progress updates.

    Allows multiple clients to connect to an optimization run and receive
    real-time progress updates during execution.
    """

    def __init__(self):
        """Initialize the optimization progress manager with empty connections."""
        # Map of optimization_id -> list of connected WebSockets
        self.connections: Dict[int, List[WebSocket]] = {}
        # Map of optimization_id -> dict of latest progress data
        self.progress_data: Dict[int, dict] = {}
        self._lock = asyncio.Lock()

    async def connect(self, optimization_id: int, websocket: WebSocket):
        """
        Add a WebSocket connection for an optimization run and send latest progress.

        Args:
            optimization_id: ID of the optimization run
            websocket: WebSocket connection to add
        """
        await websocket.accept()

        # Initialize latest_progress outside the lock
        latest_progress = None

        async with self._lock:
            if optimization_id not in self.connections:
                self.connections[optimization_id] = []
            self.connections[optimization_id].append(websocket)

            # Send latest progress data to newly connected client
            latest_progress = self.progress_data.get(optimization_id)

        # Send latest progress outside the lock to avoid blocking
        if latest_progress:
            try:
                await websocket.send_json(latest_progress)
            except Exception:
                # If sending fails, remove the connection
                await self.disconnect(optimization_id, websocket)

    async def disconnect(self, optimization_id: int, websocket: WebSocket):
        """
        Remove a WebSocket connection for an optimization run.

        Args:
            optimization_id: ID of the optimization run
            websocket: WebSocket connection to remove
        """
        async with self._lock:
            if optimization_id in self.connections:
                if websocket in self.connections[optimization_id]:
                    self.connections[optimization_id].remove(websocket)

                # Clean up empty lists
                if not self.connections[optimization_id]:
                    del self.connections[optimization_id]

    async def broadcast_progress(self, optimization_id: int, progress: dict):
        """
        Broadcast progress update to all connected clients.

        Args:
            optimization_id: ID of the optimization run
            progress: Progress data to broadcast (will be sent as JSON)
        """
        async with self._lock:
            # Store latest progress data
            self.progress_data[optimization_id] = progress

            # Get connections if any exist
            connections = (
                self.connections[optimization_id].copy()
                if optimization_id in self.connections
                else []
            )

        # Send to all active connections (outside lock to avoid blocking)
        if connections:
            disconnected = []
            for websocket in connections:
                try:
                    await websocket.send_json(progress)
                except Exception:
                    # Mark for removal if send fails
                    disconnected.append(websocket)

            # Remove disconnected clients
            if disconnected:
                async with self._lock:
                    if optimization_id in self.connections:
                        for ws in disconnected:
                            if ws in self.connections[optimization_id]:
                                self.connections[optimization_id].remove(ws)

                        # Clean up empty lists
                        if not self.connections[optimization_id]:
                            del self.connections[optimization_id]

    def has_connections(self, optimization_id: int) -> bool:
        """
        Check if there are any active connections for an optimization run.

        Args:
            optimization_id: ID of the optimization run

        Returns:
            True if there are active connections, False otherwise
        """
        return (
            optimization_id in self.connections
            and len(self.connections[optimization_id]) > 0
        )

    async def clear_progress(self, optimization_id: int):
        """
        Clear the progress data for a completed optimization.

        Args:
            optimization_id: ID of the optimization run
        """
        async with self._lock:
            if optimization_id in self.progress_data:
                del self.progress_data[optimization_id]


# Global instance
optimization_progress_manager = OptimizationProgressManager()
