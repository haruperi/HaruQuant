"""
Memory-Mapped Data Loading Module.

Provides efficient data loading for large datasets using memory-mapped files
and chunked processing. Enables backtesting on datasets larger than RAM.

Performance: Handles datasets >10GB with minimal memory footprint.
"""

from pathlib import Path
from typing import Iterator, Optional, Tuple, Union

import numpy as np
import pandas as pd

from apps.logger import logger


class MemoryMappedDataLoader:
    """
    Efficient data loader using memory-mapped files.

    Enables working with datasets larger than available RAM by mapping
    files directly to memory. Data is loaded on-demand as needed.

    Supports:
    - CSV, Parquet, and HDF5 formats
    - Chunked iteration for streaming processing
    - Automatic caching and preprocessing
    - Memory usage tracking

    Example:
        >>> loader = MemoryMappedDataLoader()
        >>> data = loader.load_mmap("large_dataset.csv")
        >>> # Or iterate in chunks
        >>> for chunk in loader.load_chunked("large_dataset.csv", chunk_size=10000):
        ...     process(chunk)
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize data loader.

        Args:
            cache_dir: Directory for cached preprocessed data.
                      If None, uses ".cache/backtest_data"
        """
        self.cache_dir = Path(cache_dir or ".cache/backtest_data")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"MemoryMappedDataLoader initialized, cache: {self.cache_dir}")

    def load_mmap(
        self,
        filepath: Union[str, Path],
        columns: Optional[list[str]] = None,
        date_column: str = "timestamp",
    ) -> pd.DataFrame:
        """
        Load data as memory-mapped array.

        For very large files, this creates a cached NumPy memory-mapped file
        for fast access without loading entire dataset into RAM.

        Args:
            filepath: Path to data file (CSV, Parquet, or HDF5)
            columns: Columns to load (None = all columns)
            date_column: Name of datetime column for index

        Returns:
            DataFrame with memory-mapped backing
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        # Check for cached version
        cache_key = self._get_cache_key(filepath, columns)
        cache_path = self.cache_dir / f"{cache_key}.npy"
        meta_path = self.cache_dir / f"{cache_key}_meta.pkl"

        if cache_path.exists() and meta_path.exists():
            logger.info(f"Loading from cache: {cache_path}")
            return self._load_from_cache(cache_path, meta_path)

        # Load and cache
        logger.info(f"Loading data from {filepath}")
        data = self._load_file(filepath, columns, date_column)

        # Cache for future use
        self._save_to_cache(data, cache_path, meta_path)

        return data

    def load_chunked(
        self,
        filepath: Union[str, Path],
        chunk_size: int = 10000,
        columns: Optional[list[str]] = None,
        date_column: str = "timestamp",
    ) -> Iterator[pd.DataFrame]:
        """
        Load data in chunks for streaming processing.

        Useful for processing very large datasets that don't fit in memory.
        Each chunk is yielded as a DataFrame.

        Args:
            filepath: Path to data file
            chunk_size: Number of rows per chunk
            columns: Columns to load (None = all)
            date_column: Name of datetime column

        Yields:
            DataFrame chunks

        Example:
            >>> for chunk in loader.load_chunked("data.csv", chunk_size=5000):
            ...     result = backtest_engine.run(chunk)
        """
        filepath = Path(filepath)

        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        file_ext = filepath.suffix.lower()

        if file_ext == ".csv":
            yield from self._load_csv_chunked(
                filepath, chunk_size, columns, date_column
            )
        elif file_ext == ".parquet":
            yield from self._load_parquet_chunked(
                filepath, chunk_size, columns, date_column
            )
        elif file_ext in [".h5", ".hdf5"]:
            yield from self._load_hdf5_chunked(
                filepath, chunk_size, columns, date_column
            )
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

    def preprocess_and_cache(
        self,
        filepath: Union[str, Path],
        columns: Optional[list[str]] = None,
        date_column: str = "timestamp",
    ) -> Path:
        """
        Preprocess and cache data file for fast future access.

        Args:
            filepath: Path to data file
            columns: Columns to include
            date_column: Datetime column name

        Returns:
            Path to cached file
        """
        filepath = Path(filepath)
        cache_key = self._get_cache_key(filepath, columns)
        cache_path = self.cache_dir / f"{cache_key}.npy"
        meta_path = self.cache_dir / f"{cache_key}_meta.pkl"

        if cache_path.exists():
            logger.info(f"Cache already exists: {cache_path}")
            return cache_path

        logger.info(f"Preprocessing {filepath}")
        data = self._load_file(filepath, columns, date_column)
        self._save_to_cache(data, cache_path, meta_path)

        logger.info(f"Cached to {cache_path}")
        return cache_path

    def clear_cache(self, filepath: Optional[Union[str, Path]] = None) -> None:
        """
        Clear cached data.

        Args:
            filepath: Specific file to clear cache for (None = clear all)
        """
        if filepath is None:
            # Clear all cache
            for file in self.cache_dir.glob("*"):
                file.unlink()
            logger.info("Cleared all cache")
        else:
            # Clear specific file cache
            filepath = Path(filepath)
            cache_key = self._get_cache_key(filepath, None)

            for pattern in [f"{cache_key}*"]:
                for file in self.cache_dir.glob(pattern):
                    file.unlink()

            logger.info(f"Cleared cache for {filepath}")

    def get_cache_size(self) -> Tuple[int, float]:
        """
        Get cache statistics.

        Returns:
            Tuple of (file_count, total_size_mb)
        """
        files = list(self.cache_dir.glob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())

        return len(files), total_size / (1024 * 1024)

    def _get_cache_key(self, filepath: Path, columns: Optional[list[str]]) -> str:
        """Generate unique cache key for file and column selection."""
        import hashlib

        # Include file path, modification time, and columns in key
        mtime = filepath.stat().st_mtime
        key_str = f"{filepath}_{mtime}"

        if columns:
            key_str += "_" + "_".join(sorted(columns))

        return hashlib.md5(key_str.encode()).hexdigest()

    def _load_file(
        self, filepath: Path, columns: Optional[list[str]], date_column: str
    ) -> pd.DataFrame:
        """Load file based on extension."""
        file_ext = filepath.suffix.lower()

        if file_ext == ".csv":
            data = pd.read_csv(filepath, usecols=columns, parse_dates=[date_column])
        elif file_ext == ".parquet":
            data = pd.read_parquet(filepath, columns=columns)
        elif file_ext in [".h5", ".hdf5"]:
            data = pd.read_hdf(filepath, columns=columns)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

        # Set datetime index
        if date_column in data.columns:
            data[date_column] = pd.to_datetime(data[date_column])
            data.set_index(date_column, inplace=True)

        return data

    def _save_to_cache(
        self, data: pd.DataFrame, cache_path: Path, meta_path: Path
    ) -> None:
        """Save DataFrame to memory-mapped cache."""
        import pickle

        # Save numeric data as memory-mapped array
        numeric_data = data.select_dtypes(include=[np.number]).values

        # Create memory-mapped file
        mmap = np.memmap(
            cache_path, dtype=np.float64, mode="w+", shape=numeric_data.shape
        )
        mmap[:] = numeric_data[:]
        mmap.flush()

        # Save metadata (columns, index)
        metadata = {
            "columns": data.select_dtypes(include=[np.number]).columns.tolist(),
            "index": data.index.tolist(),
            "shape": numeric_data.shape,
        }

        with open(meta_path, "wb") as f:
            pickle.dump(metadata, f)

        logger.debug(f"Cached {data.shape[0]} rows to {cache_path}")

    def _load_from_cache(self, cache_path: Path, meta_path: Path) -> pd.DataFrame:
        """Load DataFrame from memory-mapped cache."""
        import pickle

        # Load metadata
        with open(meta_path, "rb") as f:
            metadata = pickle.load(f)

        # Load memory-mapped array
        mmap = np.memmap(
            cache_path, dtype=np.float64, mode="r", shape=tuple(metadata["shape"])
        )

        # Create DataFrame
        data = pd.DataFrame(
            mmap, columns=metadata["columns"], index=pd.DatetimeIndex(metadata["index"])
        )

        return data

    def _load_csv_chunked(
        self,
        filepath: Path,
        chunk_size: int,
        columns: Optional[list[str]],
        date_column: str,
    ) -> Iterator[pd.DataFrame]:
        """Load CSV in chunks."""
        for chunk in pd.read_csv(
            filepath, usecols=columns, parse_dates=[date_column], chunksize=chunk_size
        ):
            if date_column in chunk.columns:
                chunk[date_column] = pd.to_datetime(chunk[date_column])
                chunk.set_index(date_column, inplace=True)
            yield chunk

    def _load_parquet_chunked(
        self,
        filepath: Path,
        chunk_size: int,
        columns: Optional[list[str]],
        date_column: str,
    ) -> Iterator[pd.DataFrame]:
        """Load Parquet in chunks."""
        import pyarrow.parquet as pq

        parquet_file = pq.ParquetFile(filepath)

        for batch in parquet_file.iter_batches(batch_size=chunk_size, columns=columns):
            chunk = batch.to_pandas()

            if date_column in chunk.columns:
                chunk[date_column] = pd.to_datetime(chunk[date_column])
                chunk.set_index(date_column, inplace=True)

            yield chunk

    def _load_hdf5_chunked(
        self,
        filepath: Path,
        chunk_size: int,
        columns: Optional[list[str]],
        date_column: str,
    ) -> Iterator[pd.DataFrame]:
        """Load HDF5 in chunks."""
        store = pd.HDFStore(filepath, mode="r")

        try:
            key = store.keys()[0]  # Use first key
            total_rows = store.get_storer(key).nrows

            for start in range(0, total_rows, chunk_size):
                chunk = store.select(
                    key, start=start, stop=start + chunk_size, columns=columns
                )

                if date_column in chunk.columns:
                    chunk[date_column] = pd.to_datetime(chunk[date_column])
                    chunk.set_index(date_column, inplace=True)

                yield chunk
        finally:
            store.close()


def estimate_memory_usage(data: pd.DataFrame) -> float:
    """
    Estimate memory usage of DataFrame in MB.

    Args:
        data: DataFrame to analyze

    Returns:
        Memory usage in megabytes
    """
    return float(data.memory_usage(deep=True).sum()) / (1024 * 1024)
