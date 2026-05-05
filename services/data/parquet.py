"""Parquet data loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import pandas as pd

from .csv import get_cached_data


def get_data_dir() -> Path:
    """Get path to data directory.

    Returns:
        Path to data directory (project_root/data)

    Example:
        >>> data_dir = get_data_dir()
        >>> print(data_dir / "dukascopy")
    """
    return Path(__file__).resolve().parents[2] / "data"


def load_parquet(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Load parquet file with caching.

    Args:
        file_path: Path to parquet file

    Returns:
        Loaded DataFrame
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    # Use absolute path as cache key to avoid ambiguity
    key = str(path.resolve())

    def _loader():
        return pd.read_parquet(path)

    return get_cached_data(key, _loader)
