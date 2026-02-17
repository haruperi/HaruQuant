"""
File Renamer Usage Examples

Purpose:
- Demonstrate batch file renaming operations
- Show pattern-based renaming (regex and string replacement)
- Illustrate prefix/suffix addition and normalization
- Examples for sequential numbering and extension changes

Key Concepts:
- Single file renaming with safety checks
- Pattern-based bulk renaming
- Prefix/suffix operations
- Sequential numbering
- Filename normalization
- Extension changes
- Dry-run mode for testing

Usage:
    python tests/usage/utils/usage_file_renamer.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.file_renamer import (
    rename_file,
    rename_with_pattern,
    add_prefix,
    add_suffix,
    rename_with_numbering,
    normalize_filenames,
    change_extension,
    batch_rename_from_mapping,
    rename_with_custom_function,
)
from apps.utils.logger import logger


def setup_test_files(test_dir):
    """Create test files for examples."""
    test_dir = Path(test_dir)
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create sample files
    test_files = [
        "EURUSD_raw_data.csv",
        "GBPUSD_raw_data.csv",
        "USDJPY_raw_data.csv",
        "Strategy Report 2024.txt",
        "Strategy Report 2025.txt",
        "backtest_results_v1.log",
        "backtest_results_v2.log",
        "Trade Log.xlsx",
        "Account Summary.xlsx",
    ]

    for filename in test_files:
        filepath = test_dir / filename
        filepath.write_text(f"Test file: {filename}")

    return test_dir


def cleanup_test_files(test_dir):
    """Clean up test files."""
    import shutil
    test_dir = Path(test_dir)
    if test_dir.exists():
        shutil.rmtree(test_dir)


def example_01_single_file_rename():
    """Example 1: Rename a single file."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Single File Rename")
    logger.info("=" * 70)

    test_dir = Path("temp_test_files") / "example01"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create test file
    old_file = test_dir / "old_name.txt"
    new_file = test_dir / "new_name.txt"
    old_file.write_text("Test content")

    logger.info(f"Original file: {old_file.name}")

    # Rename
    success = rename_file(old_file, new_file, dry_run=False)

    if success:
        logger.info(f"Renamed to: {new_file.name}")
        logger.info(f"File exists: {new_file.exists()}")
    else:
        logger.error("Rename failed")

    # Cleanup
    if new_file.exists():
        new_file.unlink()
    test_dir.rmdir()


def example_02_dry_run_mode():
    """Example 2: Test renaming with dry-run mode."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 2: Dry-Run Mode (Safe Testing)")
    logger.info("=" * 70)

    test_dir = Path("temp_test_files") / "example02"
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create test file
    test_file = test_dir / "test.txt"
    test_file.write_text("Content")

    logger.info("Testing rename with dry_run=True (no actual changes)...")

    # Dry run - file not actually renamed
    rename_file(test_file, test_dir / "renamed.txt", dry_run=True)

    logger.info(f"Original file still exists: {test_file.exists()}")
    logger.info("No actual changes made!")

    # Cleanup
    test_file.unlink()
    test_dir.rmdir()


def example_03_pattern_replacement():
    """Example 3: Rename files using pattern replacement."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 3: Pattern-Based Renaming")
    logger.info("=" * 70)

    test_dir = setup_test_files(Path("temp_test_files") / "example03")

    logger.info("Renaming files: *_raw_data.csv -> *_processed.csv")

    renamed = rename_with_pattern(
        directory=test_dir,
        pattern="_raw_data",
        replacement="_processed",
        regex=False,
        extensions=[".csv"],
        dry_run=False
    )

    logger.info(f"\nRenamed {len(renamed)} files:")
    for old, new in renamed.items():
        logger.info(f"  {Path(old).name} -> {Path(new).name}")

    cleanup_test_files(test_dir)


def example_04_regex_pattern():
    """Example 4: Use regex patterns for complex renaming."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 4: Regex Pattern Renaming")
    logger.info("=" * 70)

    test_dir = setup_test_files(Path("temp_test_files") / "example04")

    logger.info("Using regex to rename 'Report YYYY' -> 'Report_YYYY'...")

    renamed = rename_with_pattern(
        directory=test_dir,
        pattern=r"Report (\d{4})",  # Match "Report YYYY"
        replacement=r"Report_\1",   # Replace with "Report_YYYY"
        regex=True,
        extensions=[".txt"],
        dry_run=False
    )

    logger.info(f"\nRenamed {len(renamed)} files using regex:")
    for old, new in renamed.items():
        logger.info(f"  {Path(old).name} -> {Path(new).name}")

    cleanup_test_files(test_dir)


def example_05_add_prefix():
    """Example 5: Add prefix to filenames."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 5: Add Prefix to Files")
    logger.info("=" * 70)

    test_dir = setup_test_files(Path("temp_test_files") / "example05")

    logger.info("Adding 'archive_' prefix to all .log files...")

    renamed = add_prefix(
        directory=test_dir,
        prefix="archive_",
        extensions=[".log"],
        dry_run=False
    )

    logger.info(f"\nAdded prefix to {len(renamed)} files:")
    for old, new in renamed.items():
        logger.info(f"  {Path(old).name} -> {Path(new).name}")

    cleanup_test_files(test_dir)


def example_06_add_suffix():
    """Example 6: Add suffix before extension."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 6: Add Suffix to Files")
    logger.info("=" * 70)

    test_dir = setup_test_files(Path("temp_test_files") / "example06")

    # Get current date for suffix
    date_suffix = f"_{datetime.now().strftime('%Y%m%d')}"

    logger.info(f"Adding '{date_suffix}' suffix to .xlsx files...")

    renamed = add_suffix(
        directory=test_dir,
        suffix=date_suffix,
        extensions=[".xlsx"],
        dry_run=False
    )

    logger.info(f"\nAdded suffix to {len(renamed)} files:")
    for old, new in renamed.items():
        logger.info(f"  {Path(old).name} -> {Path(new).name}")

    cleanup_test_files(test_dir)


def example_07_sequential_numbering():
    """Example 7: Rename files with sequential numbers."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 7: Sequential Numbering")
    logger.info("=" * 70)

    test_dir = setup_test_files(Path("temp_test_files") / "example07")

    logger.info("Renaming .csv files with sequential numbers...")

    renamed = rename_with_numbering(
        directory=test_dir,
        base_name="data",
        start_number=1,
        padding=3,  # 001, 002, 003
        extensions=[".csv"],
        dry_run=False
    )

    logger.info(f"\nRenamed {len(renamed)} files with numbering:")
    for old, new in renamed.items():
        logger.info(f"  {Path(old).name} -> {Path(new).name}")

    cleanup_test_files(test_dir)


def example_08_normalize_filenames():
    """Example 8: Normalize filenames (lowercase, remove spaces)."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 8: Normalize Filenames")
    logger.info("=" * 70)

    test_dir = setup_test_files(Path("temp_test_files") / "example08")

    logger.info("Normalizing filenames (lowercase, spaces->underscores)...")

    renamed = normalize_filenames(
        directory=test_dir,
        lowercase=True,
        replace_spaces="_",
        remove_special_chars=False,
        dry_run=False
    )

    logger.info(f"\nNormalized {len(renamed)} files:")
    for old, new in renamed.items():
        logger.info(f"  {Path(old).name} -> {Path(new).name}")

    cleanup_test_files(test_dir)


def example_09_change_extension():
    """Example 9: Change file extensions."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 9: Change File Extensions")
    logger.info("=" * 70)

    test_dir = setup_test_files(Path("temp_test_files") / "example09")

    logger.info("Converting .log files to .txt...")

    renamed = change_extension(
        directory=test_dir,
        old_extension=".log",
        new_extension=".txt",
        dry_run=False
    )

    logger.info(f"\nChanged extension for {len(renamed)} files:")
    for old, new in renamed.items():
        logger.info(f"  {Path(old).name} -> {Path(new).name}")

    cleanup_test_files(test_dir)


def example_10_custom_function():
    """Example 10: Use custom function for renaming."""
    logger.info("\n" + "=" * 70)
    logger.info("EXAMPLE 10: Custom Rename Function")
    logger.info("=" * 70)

    test_dir = setup_test_files(Path("temp_test_files") / "example10")

    def custom_rename_logic(filename):
        """Custom logic: Add timestamp and uppercase."""
        stem = Path(filename).stem
        ext = Path(filename).suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{stem}_{timestamp}{ext}".upper()

    logger.info("Applying custom rename function to .csv files...")

    renamed = rename_with_custom_function(
        directory=test_dir,
        rename_function=custom_rename_logic,
        extensions=[".csv"],
        dry_run=False
    )

    logger.info(f"\nRenamed {len(renamed)} files with custom function:")
    for old, new in renamed.items():
        logger.info(f"  {Path(old).name} -> {Path(new).name}")

    cleanup_test_files(test_dir)


def main():
    """Run all file renamer examples."""
    logger.info("\n" + "=" * 80)
    logger.info("FILE RENAMER - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    try:
        example_01_single_file_rename()
        example_02_dry_run_mode()
        example_03_pattern_replacement()
        example_04_regex_pattern()
        example_05_add_prefix()
        example_06_add_suffix()
        example_07_sequential_numbering()
        example_08_normalize_filenames()
        example_09_change_extension()
        example_10_custom_function()

        logger.info("\n" + "=" * 80)
        logger.info("ALL EXAMPLES COMPLETED")
        logger.info("=" * 80)

        logger.info("\nKEY TAKEAWAYS:")
        logger.info("1. Always use dry_run=True first to preview changes")
        logger.info("2. rename_file() for single files, other functions for batches")
        logger.info("3. Pattern matching supports both simple strings and regex")
        logger.info("4. add_prefix() and add_suffix() for consistent naming")
        logger.info("5. normalize_filenames() for clean, consistent file names")
        logger.info("6. Sequential numbering for organizing files")
        logger.info("7. Custom functions allow complex renaming logic")

    finally:
        # Cleanup any remaining test directories
        cleanup_test_files(Path("temp_test_files"))


if __name__ == "__main__":
    main()

