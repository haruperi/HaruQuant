"""Thin read-only adapters over persisted Edge snapshot data."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from apps.sqlite.edge_discovery import EdgeDiscoveryManager


class EdgeTools:
    """Expose minimal Edge snapshot reads for early agent workflows."""

    def __init__(self, manager: Optional[EdgeDiscoveryManager] = None) -> None:
        self.manager = manager or EdgeDiscoveryManager()

    def edge_list_snapshots(
        self,
        *,
        symbol: str,
        timeframe: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """List recent snapshots for a symbol/timeframe."""
        return self.manager.get_profile_snapshots(symbol=symbol, timeframe=timeframe, limit=limit)

    def edge_get_snapshot(self, *, snapshot_id: int) -> Optional[Dict[str, Any]]:
        """Return one detailed Edge snapshot if present."""
        return self.manager.get_profile_snapshot(int(snapshot_id))

    def edge_compare_snapshots(
        self,
        *,
        left_snapshot_id: int,
        right_snapshot_id: int,
    ) -> Dict[str, Any]:
        """Compare two stored Edge snapshots."""
        return self.manager.compare_profile_snapshots(
            int(left_snapshot_id),
            int(right_snapshot_id),
        )
