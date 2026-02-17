"""
File Renamer Utility.

Provides functions for renaming files and directories with various patterns and options.
"""

import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

from apps.utils.logger import logger


def rename_file(
    old_path: Union[str, Path],
    new_path: Union[str, Path],
    overwrite: bool = False,
    dry_run: bool = False,
) -> bool:
    """
    Rename a single file.

    Args:
        old_path: Current file path
        new_path: New file path
        overwrite: If True, overwrite existing file at new_path
        dry_run: If True, only simulate the rename without executing

    Returns:
        True if rename successful (or would be successful in dry_run), False otherwise
    """
    old_path = Path(old_path)
    new_path = Path(new_path)

    if not old_path.exists():
        logger.error(f"Source file does not exist: {old_path}")
        return False

    if new_path.exists() and not overwrite:
        logger.error(f"Destination file already exists: {new_path}")
        return False

    if dry_run:
        logger.info(f"[DRY RUN] Would rename: {old_path} -> {new_path}")
        return True

    try:
        old_path.rename(new_path)
        logger.info(f"Renamed: {old_path} -> {new_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to rename {old_path} to {new_path}: {e}")
        return False


def rename_with_pattern(
    directory: Union[str, Path],
    pattern: str,
    replacement: str,
    regex: bool = False,
    recursive: bool = False,
    extensions: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, str]:
    """
    Rename multiple files in a directory using pattern matching.

    Args:
        directory: Directory containing files to rename
        pattern: Pattern to search for in filenames
        replacement: Replacement string
        regex: If True, treat pattern as regex
        recursive: If True, process subdirectories
        extensions: List of file extensions to process (e.g., ['.txt', '.py'])
        dry_run: If True, only simulate renames without executing

    Returns:
        Dictionary mapping old paths to new paths
    """
    directory = Path(directory)
    renamed_files: Dict[str, str] = {}

    if not directory.exists():
        logger.error(f"Directory does not exist: {directory}")
        return renamed_files

    # Get files to process
    if recursive:
        files = directory.rglob("*")
    else:
        files = directory.glob("*")

    for file_path in files:
        if not file_path.is_file():
            continue

        # Filter by extension if specified
        if extensions and file_path.suffix not in extensions:
            continue

        old_name = file_path.name

        # Apply pattern replacement
        if regex:
            new_name = re.sub(pattern, replacement, old_name)
        else:
            new_name = old_name.replace(pattern, replacement)

        # Skip if name unchanged
        if new_name == old_name:
            continue

        new_path = file_path.parent / new_name

        # Attempt rename
        if rename_file(file_path, new_path, overwrite=False, dry_run=dry_run):
            renamed_files[str(file_path)] = str(new_path)

    logger.info(f"Renamed {len(renamed_files)} files in {directory}")
    return renamed_files


def add_prefix(
    directory: Union[str, Path],
    prefix: str,
    recursive: bool = False,
    extensions: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, str]:
    """
    Add a prefix to filenames in a directory.

    Args:
        directory: Directory containing files to rename
        prefix: Prefix to add to filenames
        recursive: If True, process subdirectories
        extensions: List of file extensions to process
        dry_run: If True, only simulate renames

    Returns:
        Dictionary mapping old paths to new paths
    """
    directory = Path(directory)
    renamed_files = {}

    if recursive:
        files = directory.rglob("*")
    else:
        files = directory.glob("*")

    for file_path in files:
        if not file_path.is_file():
            continue

        if extensions and file_path.suffix not in extensions:
            continue

        new_name = prefix + file_path.name
        new_path = file_path.parent / new_name

        if rename_file(file_path, new_path, overwrite=False, dry_run=dry_run):
            renamed_files[str(file_path)] = str(new_path)

    return renamed_files


def add_suffix(
    directory: Union[str, Path],
    suffix: str,
    recursive: bool = False,
    extensions: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, str]:
    """
    Add a suffix to filenames (before extension) in a directory.

    Args:
        directory: Directory containing files to rename
        suffix: Suffix to add to filenames
        recursive: If True, process subdirectories
        extensions: List of file extensions to process
        dry_run: If True, only simulate renames

    Returns:
        Dictionary mapping old paths to new paths
    """
    directory = Path(directory)
    renamed_files = {}

    if recursive:
        files = directory.rglob("*")
    else:
        files = directory.glob("*")

    for file_path in files:
        if not file_path.is_file():
            continue

        if extensions and file_path.suffix not in extensions:
            continue

        new_name = file_path.stem + suffix + file_path.suffix
        new_path = file_path.parent / new_name

        if rename_file(file_path, new_path, overwrite=False, dry_run=dry_run):
            renamed_files[str(file_path)] = str(new_path)

    return renamed_files


def rename_with_numbering(
    directory: Union[str, Path],
    base_name: str,
    start_number: int = 1,
    padding: int = 3,
    recursive: bool = False,
    extensions: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, str]:
    """
    Rename files with sequential numbering.

    Args:
        directory: Directory containing files to rename
        base_name: Base name for files (e.g., 'file' -> 'file_001.txt')
        start_number: Starting number for sequence
        padding: Number of digits for zero-padding
        recursive: If True, process subdirectories
        extensions: List of file extensions to process
        dry_run: If True, only simulate renames

    Returns:
        Dictionary mapping old paths to new paths
    """
    directory = Path(directory)
    renamed_files = {}

    if recursive:
        files = sorted(directory.rglob("*"))
    else:
        files = sorted(directory.glob("*"))

    counter = start_number

    for file_path in files:
        if not file_path.is_file():
            continue

        if extensions and file_path.suffix not in extensions:
            continue

        number_str = str(counter).zfill(padding)
        new_name = f"{base_name}_{number_str}{file_path.suffix}"
        new_path = file_path.parent / new_name

        if rename_file(file_path, new_path, overwrite=False, dry_run=dry_run):
            renamed_files[str(file_path)] = str(new_path)
            counter += 1

    return renamed_files


def normalize_filenames(
    directory: Union[str, Path],
    lowercase: bool = True,
    replace_spaces: str = "_",
    remove_special_chars: bool = True,
    recursive: bool = False,
    extensions: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, str]:
    """
    Normalize filenames by applying common transformations.

    Args:
        directory: Directory containing files to rename
        lowercase: Convert to lowercase
        replace_spaces: Character to replace spaces with (None to keep spaces)
        remove_special_chars: Remove special characters (keep alphanumeric, dash, underscore)
        recursive: If True, process subdirectories
        extensions: List of file extensions to process
        dry_run: If True, only simulate renames

    Returns:
        Dictionary mapping old paths to new paths
    """
    directory = Path(directory)
    renamed_files = {}

    if recursive:
        files = directory.rglob("*")
    else:
        files = directory.glob("*")

    for file_path in files:
        if not file_path.is_file():
            continue

        if extensions and file_path.suffix not in extensions:
            continue

        stem = file_path.stem
        suffix = file_path.suffix

        # Apply transformations
        if lowercase:
            stem = stem.lower()
            suffix = suffix.lower()

        if replace_spaces:
            stem = stem.replace(" ", replace_spaces)

        if remove_special_chars:
            stem = re.sub(r"[^a-zA-Z0-9_-]", "", stem)

        new_name = stem + suffix

        if new_name == file_path.name:
            continue

        new_path = file_path.parent / new_name

        if rename_file(file_path, new_path, overwrite=False, dry_run=dry_run):
            renamed_files[str(file_path)] = str(new_path)

    return renamed_files


def rename_with_custom_function(
    directory: Union[str, Path],
    rename_function: Callable[[str], str],
    recursive: bool = False,
    extensions: Optional[List[str]] = None,
    dry_run: bool = False,
) -> Dict[str, str]:
    """
    Rename files using a custom function.

    Args:
        directory: Directory containing files to rename
        rename_function: Function that takes a filename and returns new filename
        recursive: If True, process subdirectories
        extensions: List of file extensions to process
        dry_run: If True, only simulate renames

    Returns:
        Dictionary mapping old paths to new paths
    """
    directory = Path(directory)
    renamed_files = {}

    if recursive:
        files = directory.rglob("*")
    else:
        files = directory.glob("*")

    for file_path in files:
        if not file_path.is_file():
            continue

        if extensions and file_path.suffix not in extensions:
            continue

        try:
            new_name = rename_function(file_path.name)

            if new_name == file_path.name:
                continue

            new_path = file_path.parent / new_name

            if rename_file(file_path, new_path, overwrite=False, dry_run=dry_run):
                renamed_files[str(file_path)] = str(new_path)
        except Exception as e:
            logger.error(f"Custom function failed for {file_path.name}: {e}")

    return renamed_files


def change_extension(
    directory: Union[str, Path],
    old_extension: str,
    new_extension: str,
    recursive: bool = False,
    dry_run: bool = False,
) -> Dict[str, str]:
    """
    Change file extensions.

    Args:
        directory: Directory containing files to rename
        old_extension: Current extension (e.g., '.txt')
        new_extension: New extension (e.g., '.md')
        recursive: If True, process subdirectories
        dry_run: If True, only simulate renames

    Returns:
        Dictionary mapping old paths to new paths
    """
    directory = Path(directory)
    renamed_files = {}

    # Ensure extensions start with '.'
    if not old_extension.startswith("."):
        old_extension = "." + old_extension
    if not new_extension.startswith("."):
        new_extension = "." + new_extension

    if recursive:
        files = directory.rglob(f"*{old_extension}")
    else:
        files = directory.glob(f"*{old_extension}")

    for file_path in files:
        if not file_path.is_file():
            continue

        new_name = file_path.stem + new_extension
        new_path = file_path.parent / new_name

        if rename_file(file_path, new_path, overwrite=False, dry_run=dry_run):
            renamed_files[str(file_path)] = str(new_path)

    return renamed_files


def batch_rename_from_mapping(
    mapping: Dict[str, str], dry_run: bool = False
) -> Dict[str, bool]:
    """
    Rename files based on a dictionary mapping old paths to new paths.

    Args:
        mapping: Dictionary mapping old file paths to new file paths
        dry_run: If True, only simulate renames

    Returns:
        Dictionary mapping file paths to success status
    """
    results = {}

    for old_path, new_path in mapping.items():
        success = rename_file(old_path, new_path, overwrite=False, dry_run=dry_run)
        results[old_path] = success

    successful = sum(1 for v in results.values() if v)
    logger.info(f"Successfully renamed {successful}/{len(mapping)} files")

    return results


if __name__ == "__main__":
    # Rename files in data/raw/D1 directory
    # From: AUDCAD_dukascopy-D1-No Session.csv
    # To: AUDCAD_D1.csv

    # Get the project root directory (2 levels up from this file)
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent
    data_dir = project_root / "data" / "raw" / "M1"

    logger.info(f"Starting file rename process in: {data_dir}")

    if not data_dir.exists():
        logger.error(f"Directory does not exist: {data_dir}")
    else:
        # Use regex pattern to rename files
        # Pattern matches: SYMBOL_dukascopy-D1-No Session.csv
        # Replacement keeps: SYMBOL_D1.csv
        renamed = rename_with_pattern(
            directory=data_dir,
            pattern=r"(.+)_dukascopy-M1-No Session\.csv",
            replacement=r"\1_M1.csv",
            regex=True,
            extensions=[".csv"],
            dry_run=False,  # Set to True to preview changes first
        )

        logger.info(f"Rename complete! {len(renamed)} files renamed.")

        # Display the changes
        if renamed:
            logger.info("Files renamed:")
            for old_path, new_path in renamed.items():
                old_name = Path(old_path).name
                new_name = Path(new_path).name
                logger.info(f"  {old_name} -> {new_name}")
        else:
            logger.info("No files matched the pattern.")

