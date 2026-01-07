"""State Management.

Handles persistence of trading state for pause/resume control and trade counting.
State is stored in JSON file for external control.
"""

import json
import threading
from datetime import date, datetime
from pathlib import Path
from typing import Optional


class StateManager:
    """Manage live trading state with file persistence."""

    def __init__(self, state_file: str):
        """Initialize state manager.

        Args:
            state_file: Path to state JSON file
        """
        self.state_file = Path(state_file)
        self._lock = threading.Lock()
        self._state = self._load_or_create_state()

    def _load_or_create_state(self) -> dict:
        """Load existing state or create default state."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)

                # Ensure all required fields exist
                state.setdefault("enabled", True)
                state.setdefault("paused", False)
                state.setdefault("last_run", None)
                state.setdefault("trade_count_today", 0)
                state.setdefault("last_reset_date", str(date.today()))

                return dict(state)

            except (json.JSONDecodeError, Exception) as e:
                print(f"Warning: Failed to load state file, creating new state: {e}")

        # Create default state
        return {
            "enabled": True,
            "paused": False,
            "last_run": None,
            "trade_count_today": 0,
            "last_reset_date": str(date.today()),
        }

    def _save_state(self):
        """Save current state to file."""
        try:
            # Create directory if it doesn't exist
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)

        except Exception as e:
            print(f"Error saving state: {e}")

    def is_enabled(self) -> bool:
        """Check if trading is enabled.

        Returns:
            True if trading is enabled
        """
        with self._lock:
            # Reload from file to catch external changes
            self._state = self._load_or_create_state()
            return bool(self._state.get("enabled", True))

    def is_paused(self) -> bool:
        """Check if trading is paused.

        Returns:
            True if trading is paused
        """
        with self._lock:
            # Reload from file to catch external changes
            self._state = self._load_or_create_state()
            return bool(self._state.get("paused", False))

    def pause(self):
        """Pause trading temporarily."""
        with self._lock:
            self._state["paused"] = True
            self._save_state()

    def resume(self):
        """Resume trading from pause."""
        with self._lock:
            self._state["paused"] = False
            self._save_state()

    def enable(self):
        """Enable trading."""
        with self._lock:
            self._state["enabled"] = True
            self._state["paused"] = False
            self._save_state()

    def disable(self):
        """Disable trading completely."""
        with self._lock:
            self._state["enabled"] = False
            self._save_state()

    def update_last_run(self, timestamp: Optional[datetime] = None):
        """Update last run timestamp.

        Args:
            timestamp: Timestamp to set (defaults to now)
        """
        with self._lock:
            if timestamp is None:
                timestamp = datetime.now()

            self._state["last_run"] = timestamp.isoformat()
            self._save_state()

    def get_last_run(self) -> Optional[datetime]:
        """Get last run timestamp.

        Returns:
            Last run timestamp or None
        """
        with self._lock:
            last_run = self._state.get("last_run")
            if last_run:
                return datetime.fromisoformat(last_run)
            return None

    def increment_trade_count(self) -> int:
        """Increment daily trade count and return new count.

        Returns:
            Updated trade count
        """
        with self._lock:
            # Check if we need to reset the counter (new day)
            self._check_and_reset_daily_counter()

            self._state["trade_count_today"] += 1
            self._save_state()

            return int(self._state["trade_count_today"])

    def get_trade_count_today(self) -> int:
        """Get today's trade count.

        Returns:
            Number of trades executed today
        """
        with self._lock:
            # Check if we need to reset the counter (new day)
            self._check_and_reset_daily_counter()

            return int(self._state.get("trade_count_today", 0))

    def _check_and_reset_daily_counter(self):
        """Check if date changed and reset counter if needed."""
        today = str(date.today())
        last_reset = self._state.get("last_reset_date")

        if last_reset != today:
            self._state["trade_count_today"] = 0
            self._state["last_reset_date"] = today
            self._save_state()

    def reset_daily_counter(self):
        """Manually reset daily trade counter."""
        with self._lock:
            self._state["trade_count_today"] = 0
            self._state["last_reset_date"] = str(date.today())
            self._save_state()

    def get_state_summary(self) -> dict:
        """Get summary of current state.

        Returns:
            Dictionary with state information
        """
        with self._lock:
            self._state = self._load_or_create_state()
            return {
                "enabled": self._state.get("enabled"),
                "paused": self._state.get("paused"),
                "last_run": self._state.get("last_run"),
                "trade_count_today": self._state.get("trade_count_today"),
                "last_reset_date": self._state.get("last_reset_date"),
            }

    def __repr__(self) -> str:
        """Return string representation of StateManager."""
        summary = self.get_state_summary()
        return (
            f"StateManager(enabled={summary['enabled']}, "
            f"paused={summary['paused']}, "
            f"trades_today={summary['trade_count_today']})"
        )
