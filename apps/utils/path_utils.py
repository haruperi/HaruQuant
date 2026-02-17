"""Platform-independent path helpers based on pathlib."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union


PathLike = Union[str, Path]


def normalize_path(path: PathLike, base: Optional[PathLike] = None) -> Path:
    """
    Normalize to pathlib.Path and optionally resolve relative to a base directory.
    """
    p = Path(path)
    if base is not None and not p.is_absolute():
        p = Path(base) / p
    return p.expanduser()


def ensure_parent_dir(path: PathLike) -> Path:
    """
    Ensure parent directory exists for a file path.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def ensure_dir(path: PathLike) -> Path:
    """
    Ensure directory path exists.
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p

