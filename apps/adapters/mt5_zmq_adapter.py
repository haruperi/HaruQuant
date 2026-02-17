"""MT5 MQL5 EA ZeroMQ subscriber adapter."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Iterable, Optional

from apps.adapters.normalization import ProgressCallback, normalize_mt5_event
from apps.utils.logger import logger

try:
    import zmq
except Exception:  # pragma: no cover - optional dependency
    zmq = None  # type: ignore


class MT5ZmqAdapter:
    """Subscribe to MT5 EA PUB stream and normalize tick/bar events."""

    def __init__(
        self,
        endpoint: str,
        topics: Optional[Iterable[str]] = None,
        recv_timeout_ms: int = 1000,
    ) -> None:
        if zmq is None:
            raise RuntimeError("pyzmq is required for MT5ZmqAdapter")
        self.endpoint = endpoint
        self.topics = list(topics or [""])
        self.recv_timeout_ms = recv_timeout_ms
        self._ctx: Optional[Any] = None
        self._sock: Optional[Any] = None

    def start(self) -> None:
        if self._sock is not None:
            return
        self._ctx = zmq.Context.instance()
        self._sock = self._ctx.socket(zmq.SUB)
        self._sock.setsockopt(zmq.RCVTIMEO, self.recv_timeout_ms)
        self._sock.setsockopt(zmq.LINGER, 0)
        for topic in self.topics:
            self._sock.setsockopt_string(zmq.SUBSCRIBE, topic)
        self._sock.connect(self.endpoint)
        logger.info(f"MT5 ZMQ adapter connected to {self.endpoint}")

    def stop(self) -> None:
        if self._sock is None:
            return
        self._sock.close(0)
        self._sock = None
        logger.info("MT5 ZMQ adapter stopped")

    def _decode_message(self) -> Optional[Dict[str, Any]]:
        if self._sock is None:
            raise RuntimeError("Adapter is not started")
        try:
            parts = self._sock.recv_multipart()
        except zmq.Again:
            return None

        if len(parts) == 1:
            raw = parts[0].decode("utf-8")
            if " " in raw:
                _, payload_str = raw.split(" ", 1)
            else:
                payload_str = raw
        elif len(parts) >= 2:
            payload_str = parts[-1].decode("utf-8")
        else:
            return None

        payload = json.loads(payload_str)
        if not isinstance(payload, dict):
            raise ValueError("Incoming ZMQ payload must be a JSON object")
        return payload

    def receive(self) -> Optional[Dict[str, Any]]:
        """Receive one message and normalize it into canonical form."""
        payload = self._decode_message()
        if payload is None:
            return None
        canonical, error = normalize_mt5_event(payload)
        if error is not None:
            logger.warning(f"MT5 ZMQ normalize rejected payload: {error}")
            return None
        return canonical

    def ingest(
        self,
        expected_count: int,
        progress_callback: Optional[ProgressCallback] = None,
        max_wait_seconds: float = 30.0,
    ) -> list[Dict[str, Any]]:
        """Ingest N canonical messages with optional progress callbacks."""
        if expected_count <= 0:
            return []
        records: list[Dict[str, Any]] = []
        started = time.monotonic()
        while len(records) < expected_count:
            rec = self.receive()
            if rec is None:
                if (time.monotonic() - started) >= max_wait_seconds:
                    raise TimeoutError(
                        f"Timed out waiting for {expected_count} messages, got {len(records)}"
                    )
                continue
            records.append(rec)
            if progress_callback is not None:
                progress_pct = (len(records) / expected_count) * 100.0
                progress_callback(len(records), expected_count, progress_pct)
        return records
