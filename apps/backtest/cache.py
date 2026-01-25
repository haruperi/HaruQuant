"""
Result Caching Module.

Provides caching and serialization capabilities for backtest results.
Enables fast reloading of previous results and avoids redundant calculations.

Performance: 10-100x speedup for repeated backtests with same parameters.
"""

import hashlib
import pickle
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, cast

import pandas as pd

from apps.logger import logger

from .result import BacktestResult


class ResultCache:
    """
    Disk-based cache for backtest results with LRU eviction.

    Caches complete BacktestResult objects to disk for fast reload.
    Automatically manages cache size and evicts old entries.

    Features:
    - Automatic cache key generation from parameters
    - LRU eviction when cache size limit reached
    - Cache statistics and monitoring
    - Automatic cleanup of stale entries

    Example:
        >>> cache = ResultCache(max_size_mb=1000)
        >>>
        >>> # Try to get cached result
        >>> result = cache.get(strategy_name="MyStrategy", symbol="EURUSD", params={...})
        >>>
        >>> if result is None:
        ...     # Run backtest
        ...     result = engine.run()
        ...     # Cache for future use
        ...     cache.put(result, strategy_name="MyStrategy", symbol="EURUSD", params={...})
    """

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        max_size_mb: float = 1000.0,
        max_age_days: int = 30,
    ):
        """
        Initialize result cache.

        Args:
            cache_dir: Directory for cached results.
                      If None, uses ".cache/backtest_results"
            max_size_mb: Maximum cache size in megabytes
            max_age_days: Maximum age of cached entries in days
        """
        self.cache_dir = Path(cache_dir or ".cache/backtest_results")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.max_age = timedelta(days=max_age_days)

        logger.info(
            f"ResultCache initialized: {self.cache_dir}, "
            f"max_size={max_size_mb}MB, max_age={max_age_days}d"
        )

        # Clean up stale entries on init
        self._cleanup_stale()

    def get(
        self,
        strategy_name: str,
        symbol: str,
        params: Dict[str, Any],
        data_hash: Optional[str] = None,
    ) -> Optional[BacktestResult]:
        """
        Get cached result if available.

        Args:
            strategy_name: Name of strategy
            symbol: Trading symbol
            params: Strategy parameters dict
            data_hash: Optional hash of data (for cache invalidation)

        Returns:
            BacktestResult if cached, None otherwise
        """
        cache_key = self._generate_key(strategy_name, symbol, params, data_hash)
        cache_path = self.cache_dir / f"{cache_key}.pkl"

        if not cache_path.exists():
            logger.debug(f"Cache miss: {cache_key}")
            return None

        try:
            with open(cache_path, "rb") as f:
                result = pickle.load(f)

            logger.info(f"Cache hit: {cache_key}")

            # Update access time for LRU
            cache_path.touch()

            return cast(Optional[BacktestResult], result)

        except Exception as e:
            logger.warning(f"Failed to load cached result: {e}")
            # Remove corrupted cache file
            cache_path.unlink(missing_ok=True)
            return None

    def put(
        self,
        result: BacktestResult,
        strategy_name: str,
        symbol: str,
        params: Dict[str, Any],
        data_hash: Optional[str] = None,
    ) -> None:
        """
        Cache a backtest result.

        Args:
            result: BacktestResult to cache
            strategy_name: Name of strategy
            symbol: Trading symbol
            params: Strategy parameters dict
            data_hash: Optional hash of data
        """
        cache_key = self._generate_key(strategy_name, symbol, params, data_hash)
        cache_path = self.cache_dir / f"{cache_key}.pkl"

        try:
            with open(cache_path, "wb") as f:
                pickle.dump(result, f, protocol=pickle.HIGHEST_PROTOCOL)

            logger.info(f"Cached result: {cache_key}")

            # Check cache size and evict if needed
            self._enforce_size_limit()

        except Exception as e:
            logger.error(f"Failed to cache result: {e}")

    def invalidate(
        self, strategy_name: Optional[str] = None, symbol: Optional[str] = None
    ) -> int:
        """
        Invalidate cached results.

        Args:
            strategy_name: Invalidate all results for this strategy (None = all)
            symbol: Invalidate all results for this symbol (None = all)

        Returns:
            Number of entries invalidated
        """
        count = 0

        for cache_file in self.cache_dir.glob("*.pkl"):
            # If no filters, delete all
            if strategy_name is None and symbol is None:
                cache_file.unlink()
                count += 1
                continue

            # Try to load and check filters
            try:
                with open(cache_file, "rb") as f:
                    result = pickle.load(f)

                should_delete = True

                if strategy_name and result.strategy_name != strategy_name:
                    should_delete = False

                if symbol and result.symbol != symbol:
                    should_delete = False

                if should_delete:
                    cache_file.unlink()
                    count += 1

            except Exception:
                # If we can't load it, delete it
                cache_file.unlink()
                count += 1

        logger.info(f"Invalidated {count} cache entries")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache statistics
        """
        files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in files)

        if files:
            oldest = min(f.stat().st_mtime for f in files)
            newest = max(f.stat().st_mtime for f in files)
            oldest_dt = datetime.fromtimestamp(oldest)
            newest_dt = datetime.fromtimestamp(newest)
        else:
            oldest_dt = None
            newest_dt = None

        return {
            "entry_count": len(files),
            "total_size_mb": total_size / (1024 * 1024),
            "max_size_mb": self.max_size_bytes / (1024 * 1024),
            "utilization_percent": (
                (total_size / self.max_size_bytes * 100)
                if self.max_size_bytes > 0
                else 0
            ),
            "oldest_entry": oldest_dt,
            "newest_entry": newest_dt,
            "cache_dir": str(self.cache_dir),
        }

    def clear(self) -> int:
        """
        Clear all cached results.

        Returns:
            Number of entries cleared
        """
        return self.invalidate()

    def _generate_key(
        self,
        strategy_name: str,
        symbol: str,
        params: Dict[str, Any],
        data_hash: Optional[str],
    ) -> str:
        """
        Generate unique cache key from parameters.

        Args:
            strategy_name: Strategy name
            symbol: Symbol
            params: Parameters dict
            data_hash: Optional data hash

        Returns:
            Unique cache key string
        """
        # Sort params for consistent hashing
        sorted_params = sorted(params.items())

        key_components = [strategy_name, symbol, str(sorted_params)]

        if data_hash:
            key_components.append(data_hash)

        key_str = "|".join(key_components)

        # Generate hash
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def _enforce_size_limit(self) -> None:
        """Enforce cache size limit by evicting oldest entries."""
        files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in files)

        if total_size <= self.max_size_bytes:
            return

        # Sort by access time (oldest first)
        files.sort(key=lambda f: f.stat().st_atime)

        # Evict oldest until under limit
        evicted = 0
        for idx, file in enumerate(files, start=1):
            if total_size <= self.max_size_bytes:
                break

            file_size = file.stat().st_size
            file.unlink()
            total_size -= file_size
            evicted = idx

        if evicted > 0:
            logger.info(f"Evicted {evicted} cache entries to enforce size limit")

    def _cleanup_stale(self) -> None:
        """Remove cache entries older than max_age."""
        now = datetime.now()
        cutoff = now - self.max_age

        removed = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)

            if mtime < cutoff:
                cache_file.unlink()
                removed += 1

        if removed > 0:
            logger.info(f"Removed {removed} stale cache entries")


def compute_data_hash(data: pd.DataFrame) -> str:
    """
    Compute a DataFrame hash for cache invalidation.

    Args:
        data: DataFrame to hash

    Returns:
        Hash string
    """
    # Hash based on shape, columns, and sample of data
    hash_components = [
        str(data.shape),
        str(data.columns.tolist()),
        str(data.index[0]) if len(data) > 0 else "",
        str(data.index[-1]) if len(data) > 0 else "",
        str(data.iloc[0].values.tolist()) if len(data) > 0 else "",
        str(data.iloc[-1].values.tolist()) if len(data) > 0 else "",
    ]

    hash_str = "|".join(hash_components)
    return hashlib.md5(hash_str.encode()).hexdigest()[:16]


# Cached metric calculations
# These use functools.lru_cache to avoid recomputing expensive metrics


@lru_cache(maxsize=128)
def cached_sharpe_ratio(returns_tuple: tuple, risk_free_rate: float = 0.0) -> float:
    """
    Calculate cached Sharpe ratio.

    Args:
        returns_tuple: Tuple of returns (for hashability)
        risk_free_rate: Risk-free rate

    Returns:
        Sharpe ratio
    """
    import numpy as np

    returns = np.array(returns_tuple)
    excess_returns = returns - risk_free_rate

    if len(excess_returns) == 0 or np.std(excess_returns) == 0:
        return 0.0

    return float(np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252))


@lru_cache(maxsize=128)
def cached_max_drawdown(equity_tuple: tuple) -> float:
    """
    Calculate cached maximum drawdown.

    Args:
        equity_tuple: Tuple of equity values (for hashability)

    Returns:
        Maximum drawdown percentage
    """
    import numpy as np

    equity = np.array(equity_tuple)

    if len(equity) == 0:
        return 0.0

    running_max = np.maximum.accumulate(equity)
    drawdown = (running_max - equity) / running_max * 100

    return float(np.max(drawdown))


@lru_cache(maxsize=128)
def cached_sortino_ratio(returns_tuple: tuple, risk_free_rate: float = 0.0) -> float:
    """
    Calculate cached Sortino ratio.

    Args:
        returns_tuple: Tuple of returns (for hashability)
        risk_free_rate: Risk-free rate

    Returns:
        Sortino ratio
    """
    import numpy as np

    returns = np.array(returns_tuple)
    excess_returns = returns - risk_free_rate

    # Only consider downside deviation
    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) == 0:
        return 0.0

    downside_std = np.std(downside_returns)

    if downside_std == 0:
        return 0.0

    return float(np.mean(excess_returns) / downside_std * np.sqrt(252))
