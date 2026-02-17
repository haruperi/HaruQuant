# Apps/Utils Usage Examples

Comprehensive usage examples for all utilities in the `apps/utils` module.

## Overview

This directory contains 9 usage example files, each demonstrating a specific utility module with 5-10 practical examples.

## Files and Examples

### 1. usage_security.py - Security Utilities
**Purpose**: Password hashing and data encryption for secure credential storage

**Examples**:
1. Basic password hashing with bcrypt
2. User authentication system simulation
3. Password hash uniqueness demonstration
4. Basic data encryption/decryption
5. MT5 credentials encryption
6. Configuration file encryption
7. API key management system
8. Wrong encryption key handling
9. Trading strategy parameter encryption
10. Security best practices summary

**Run**:
```bash
python tests/usage/utils/usage_security.py
```

**Key Concepts**: bcrypt password hashing, Fernet symmetric encryption, secure key management

---

### 2. usage_data_getters.py - Data Loading
**Purpose**: Load market data from multiple sources (MT5, Dukascopy, Parquet)

**Examples**:
1. Get project data directory path
2. Basic Dukascopy data loading
3. Load data by bar count
4. MT5 data loading with Dukascopy fallback
5. MT5 data by date range
6. Load data from Parquet files
7. Data caching mechanism
8. Load multiple symbols
9. Timezone handling
10. Data validation integration

**Run**:
```bash
python tests/usage/utils/usage_data_getters.py
```

**Key Concepts**: MT5 connection, Dukascopy API, data caching, timezone conversion

---

### 3. usage_data_validator.py - Data Quality Validation
**Purpose**: Validate market data quality and detect issues

**Examples**:
1. Basic price sanity validation
2. Gap detection in time series
3. Spike and anomaly detection
4. Missing timestamp detection
5. Comprehensive validation
6. Data quality report generation
7. Automated data cleaning
8. Zero volume detection
9. Duplicate timestamp detection
10. Spread statistics analysis

**Run**:
```bash
python tests/usage/utils/usage_data_validator.py
```

**Key Concepts**: OHLC validation, gap detection, anomaly detection, quality scoring

---

### 4. usage_data_manipulator.py - Timeframe Management
**Purpose**: Resample data between timeframes and aggregate bars

**Examples**:
1. Basic timeframe resampling (M1 → M5)
2. Multi-timeframe resampling
3. Timeframe validation and conversion
4. Bar aggregation from ticks
5. Aggregate M1 to M5 bars
6. Signal mapping across timeframes
7. OHLC preservation verification
8. Spread handling in resampling
9. Live trading simulation
10. Performance comparison (vectorized vs iterative)

**Run**:
```bash
python tests/usage/utils/usage_data_manipulator.py
```

**Key Concepts**: TimeframeManager, BarAggregator, OHLC preservation, live aggregation

---

### 5. usage_multitasking.py - Concurrent Execution
**Purpose**: Execute tasks concurrently using threads or processes

**Examples**:
1. Basic async task execution
2. Multiple concurrent tasks
3. Thread pools with limits
4. Process engine for CPU-bound tasks
5. Task monitoring
6. Parallel backtest simulation
7. Parameter optimization grid
8. Pool configuration
9. Parallel data loading
10. Error handling in tasks

**Run**:
```bash
python tests/usage/utils/usage_multitasking.py
```

**Key Concepts**: @task decorator, thread/process pools, concurrent backtesting

---

### 6. usage_file_renamer.py - File Operations
**Purpose**: Batch file renaming with various patterns

**Examples**:
1. Single file rename
2. Dry-run mode (safe testing)
3. Pattern-based renaming
4. Regex pattern renaming
5. Add prefix to files
6. Add suffix to files
7. Sequential numbering
8. Normalize filenames
9. Change file extensions
10. Custom rename function

**Run**:
```bash
python tests/usage/utils/usage_file_renamer.py
```

**Key Concepts**: Pattern matching, regex, prefix/suffix, normalization

---

### 7. usage_data_comparator.py - DataFrame Comparison
**Purpose**: Compare DataFrames for equality and differences

**Examples**:
1. Identical DataFrames comparison
2. DataFrames with differences
3. Tolerance-based comparison
4. Specific column comparison
5. Single column comparison
6. DateTime alignment
7. OHLCV-specific comparison
8. OHLC-only comparison
9. Compare data from different sources
10. Index comparison

**Run**:
```bash
python tests/usage/utils/usage_data_comparator.py
```

**Key Concepts**: compare_dataframes, tolerance settings, datetime alignment, OHLCV helpers

---

### 8. usage_error_description.py - MT5 Error Codes
**Purpose**: Look up MT5 error code descriptions

**Examples**:
1. Basic error code lookup
2. Success and completion codes
3. Order rejection errors
4. Invalid parameter errors
5. Market condition errors
6. Account and margin errors
7. Position and order errors
8. Runtime and system errors
9. Chart and indicator errors
10. Error handling pattern

**Run**:
```bash
python tests/usage/utils/usage_error_description.py
```

**Key Concepts**: TradeErrorDescriptions, error categories, error handling patterns

---

### 9. usage_validate.py - Trading Parameter Validation
**Purpose**: Validate trading parameters before execution

**Examples**:
1. Symbol validation
2. Volume validation
3. Volume with symbol-specific limits
4. Price validation
5. Stop loss validation
6. Take profit validation
7. Order type validation
8. Timeframe validation
9. Date range validation
10. Trade request validation
11. Batch validation
12. Magic number validation
13. Price deviation validation
14. MT5 credentials validation
15. Validation rules management

**Run**:
```bash
python tests/usage/utils/usage_validate.py
```

**Key Concepts**: TradeValidator, parameter validation, validation rules, batch validation

---

## Running All Examples

To run all examples sequentially:

```bash
for file in tests/usage/utils/usage_*.py; do
    echo "Running $file..."
    python "$file"
    echo "---"
done
```

Or on Windows PowerShell:
```powershell
Get-ChildItem tests\usage\utils\usage_*.py | ForEach-Object {
    Write-Host "Running $($_.Name)..."
    python $_.FullName
    Write-Host "---"
}
```

## Common Patterns

### Import Pattern
All examples follow this structure:
```python
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from apps.utils.module_name import functions
from apps.utils.logger import logger
```

### Example Function Pattern
```python
def example_01_description():
    """Example 1: What this example demonstrates."""
    logger.info("=" * 70)
    logger.info("EXAMPLE 1: Title")
    logger.info("=" * 70)

    # Example code here

    logger.info("Results...")
```

### Main Function Pattern
```python
def main():
    """Run all examples."""
    logger.info("\n" + "=" * 80)
    logger.info("MODULE NAME - COMPREHENSIVE USAGE EXAMPLES")
    logger.info("=" * 80)

    example_01_description()
    example_02_description()
    # ... more examples

    logger.info("\nKEY TAKEAWAYS:")
    logger.info("1. First takeaway")
    logger.info("2. Second takeaway")

if __name__ == "__main__":
    main()
```

## Dependencies

- Python 3.8+
- pandas
- numpy
- cryptography (for security)
- passlib (for password hashing)
- MetaTrader 5 (for MT5 examples)

## Best Practices

1. **Always test with dry_run**: When using file operations or risky operations
2. **Use validation**: Always validate parameters before trading
3. **Check error codes**: Always check MT5 operation return codes
4. **Cache data**: Enable caching for repeated data loads
5. **Validate data quality**: Run validation on all market data
6. **Use appropriate tolerances**: Set proper float comparison tolerances
7. **Encrypt sensitive data**: Always encrypt credentials and API keys

## Integration with Trading Platform

These utilities are designed to work together:

```python
# Load and validate data
from apps.utils.data_getters import load_mt5
from apps.utils.data_validator import DataValidator

data = load_mt5("EURUSD", "H1", count=1000)
validator = DataValidator()
report = validator.validate(data, return_report=True)

# Resample if needed
if report.quality_score > 95:
    from apps.utils.data_manipulator import TimeframeManager
    manager = TimeframeManager()
    h4_data = manager.resample(data, 'H4', 'H1')

# Validate trade parameters
from apps.utils.validate import TradeValidator
validator = TradeValidator()
is_valid, msg = validator.validate('volume', 0.1, symbol='EURUSD')
```

## Contributing

When adding new examples:
1. Follow the established pattern
2. Include 5-10 examples per file
3. Add clear docstrings
4. Include practical, real-world scenarios
5. Update this README with the new examples

## Support

For issues or questions:
- Check the main utility module documentation in `apps/utils/`
- Review the example code for similar use cases
- Consult the logger output for detailed error messages

