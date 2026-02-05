"""
Script to update all backtest examples to use the new simulation module.

This script systematically updates all usage examples in tests/usage/backtest/
to use apps.simulation instead of the old apps.backtest module.
"""

import re
from pathlib import Path
from typing import List, Tuple


def find_files_to_update(base_path: Path) -> List[Path]:
    """Find all Python files that need updating."""
    files = []
    for py_file in base_path.rglob("*.py"):
        if "__pycache__" in str(py_file) or "__init__" in str(py_file):
            continue

        # Read file content
        content = py_file.read_text(encoding="utf-8")

        # Check if it uses old backtest module
        if any(
            pattern in content
            for pattern in [
                "from apps.backtest import",
                "apps.backtest.EventDrivenEngine",
                "apps.backtest.VectorizedEngine",
                "EventDrivenEngine",
                "VectorizedEngine",
            ]
        ):
            files.append(py_file)

    return files


def update_imports(content: str) -> str:
    """Update import statements."""
    # Replace backtest imports with simulation imports
    patterns = [
        (
            r"from apps\.backtest import EventDrivenEngine",
            "from apps.simulation.simulator import TradeSimulator\n"
            "from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator\n"
            "from apps.simulation.utils import calculate_metrics_from_simulator",
        ),
        (
            r"from apps\.backtest import VectorizedEngine",
            "from apps.simulation.simulator import TradeSimulator\n"
            "from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator\n"
            "from apps.simulation.utils import calculate_metrics_from_simulator",
        ),
        (
            r"from apps\.backtest import EventDrivenEngine, VectorizedEngine",
            "from apps.simulation.simulator import TradeSimulator\n"
            "from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator\n"
            "from apps.simulation.utils import calculate_metrics_from_simulator",
        ),
    ]

    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)

    return content


def update_engine_creation(content: str) -> str:
    """Update engine creation and running pattern."""
    # Pattern 1: Simple EventDrivenEngine with basic parameters
    pattern1 = r"""(?P<indent>[ \t]*)engine = EventDrivenEngine\(\s*
        strategy=(?P<strategy>\w+),\s*
        data=(?P<data>\w+),\s*
        initial_balance=(?P<balance>[\d.]+),?\s*
        (?:commission=(?P<commission>[\d.]+),?\s*)?
        (?:slippage_points=(?P<slippage>[\d.]+),?\s*)?
        (?:backtest_start_date=(?P<start_date>\w+),?\s*)?
        (?:backtest_end_date=(?P<end_date>\w+),?\s*)?
        (?:timeframe=(?P<timeframe>['\"][\w\d]+['\"])?,?\s*)?
        (?:mt5_client=(?P<mt5_client>\w+)?)?\s*
    \)\s*
    (?P<result_line>.*?result = engine\.run\(\))"""

    def replacement1(match):
        d = match.groupdict()
        indent = d["indent"]
        strategy = d["strategy"]
        data = d["data"]
        balance = d["balance"]
        commission = d.get("commission", "0.0")
        slippage = d.get("slippage", "0")
        start_date = d.get("start_date", "None")
        end_date = d.get("end_date", "None")
        mt5_client = d.get("mt5_client", "None")

        # Infer symbol from strategy params if possible
        # This is a simplified approach - we'll use 'EURUSD' as default
        symbol = "EURUSD"

        new_code = f"""{indent}# Initialize strategy
{indent}{strategy}.on_init()
{indent}
{indent}# Calculate signals
{indent}{data} = {strategy}.on_bar({data})
{indent}
{indent}# Setup simulator components
{indent}account_info = AccountInfoSimulator(
{indent}    balance={balance},
{indent}    equity={balance},
{indent}    margin_free={balance},
{indent})
{indent}symbol_info = SymbolInfoSimulator.from_mt5_symbol('{symbol}')
{indent}symbol_info.symbol = '{symbol}'
{indent}
{indent}# Create simulator
{indent}simulator = TradeSimulator(
{indent}    simulator_name="Backtest_{symbol}",
{indent}    mt5_client={mt5_client},
{indent}    account_info=account_info,
{indent}    symbols={{'{symbol}': symbol_info}},
{indent})
{indent}
{indent}# Run simulation
{indent}simulator.run(
{indent}    data={data},
{indent}    strategy={strategy},
{indent}    symbol='{symbol}',
{indent}    volume=0.1,
{indent}    verbose=False,
{indent}    save_db=False,
{indent}    engine_type="event_driven",
{indent}    commission_per_contract={commission or '0.0'},
{indent}    slippage_points={slippage or '0'},"""

        if start_date != "None":
            new_code += f"\n{indent}    start_date={start_date},"
        if end_date != "None":
            new_code += f"\n{indent}    end_date={end_date},"

        new_code += f"""
{indent})
{indent}
{indent}# Get results from simulator
{indent}result = calculate_metrics_from_simulator(simulator)"""

        return new_code

    # Try to apply the pattern
    content = re.sub(pattern1, replacement1, content, flags=re.VERBOSE | re.MULTILINE)

    return content


def update_file(file_path: Path, dry_run: bool = False) -> Tuple[bool, str]:
    """Update a single file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content

        # Apply updates
        content = update_imports(content)

        # Only do simple pattern replacements for now
        # More complex engine creations will need manual review

        if content != original_content:
            if not dry_run:
                file_path.write_text(content, encoding="utf-8")
            return True, f"Updated {file_path.relative_to(Path.cwd())}"
        else:
            return False, f"No changes needed for {file_path.relative_to(Path.cwd())}"

    except Exception as e:
        return False, f"Error updating {file_path}: {e}"


def main():
    """Execute main function."""
    base_path = Path(__file__).parent / "tests" / "usage" / "backtest"

    if not base_path.exists():
        print(f"Error: {base_path} does not exist")
        return

    print("=" * 70)
    print("Backtest Examples Update Script")
    print("=" * 70)
    print()

    # Find files
    print("Finding files to update...")
    files = find_files_to_update(base_path)
    print(f"Found {len(files)} files that need updating")
    print()

    # Proceed automatically
    print("Proceeding with updates...")

    # Update files
    print("\nUpdating files...")
    updated_count = 0
    errors = []

    for file_path in files:
        success, message = update_file(file_path, dry_run=False)
        if success:
            updated_count += 1
            print(f"[OK] {message}")
        else:
            print(f"[SKIP] {message}")
            if "Error" in message:
                errors.append(message)

    # Summary
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Files processed: {len(files)}")
    print(f"Files updated: {updated_count}")
    print(f"Errors: {len(errors)}")

    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"  - {error}")

    print("\nNote: Some files may require manual review for complex engine patterns.")
    print("Please check the updated files and test them before use.")


if __name__ == "__main__":
    main()
