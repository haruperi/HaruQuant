"""Comprehensive script to update all remaining backtest examples to use apps.simulation."""

import re
from pathlib import Path
from typing import Tuple


def fix_mt5_client_pattern(content: str) -> str:
    """Fix MT5Client initialization to use connect() method."""
    # Pattern 1: Constructor with parameters
    pattern1 = r'client = MT5Client\(\s*login=creds\["login"\],\s*password=creds\["password"\],\s*server=creds\["server"\],\s*path=creds\["path"\]\s*\)'
    replacement1 = """client = MT5Client()
    if not client.connect(creds["path"], creds["login"], creds["password"], creds["server"]):
        raise ConnectionError("Failed to connect to MT5")"""
    content = re.sub(pattern1, replacement1, content, flags=re.MULTILINE)

    # Pattern 2: with context manager
    pattern2 = r"with get_mt5_client\(\) as client:\s*\n\s*if not client\.is_connected\(\):\s*\n\s*raise ConnectionError\([^\)]+\)\s*\n\s*\n\s*df = client\.get_bars\("
    replacement2 = """client = get_mt5_client()
    try:
        df = client.get_bars("""
    content = re.sub(pattern2, replacement2, content, flags=re.MULTILINE)

    # Add finally block if needed
    if "client = get_mt5_client()" in content and "finally:" not in content:
        # Find the return df statement and add finally before it
        content = re.sub(
            r"(\s+)(if df\.empty:.*?return df)",
            r"\1\2\n\1finally:\n\1    client.shutdown()",
            content,
            flags=re.DOTALL,
        )

    return content


def fix_trades_dataframe(content: str) -> str:
    """Fix trades DataFrame creation to use get_trades_df()."""
    # Pattern: pd.DataFrame([t.to_dict() for t in result.trades])
    pattern = r"if len\(result\.trades\) > 0:\s*\n\s*trades_df = pd\.DataFrame\(\[t\.to_dict\(\) for t in result\.trades\]\)\s*\n\s*else:\s*\n\s*[^\n]+\s*\n\s*trades_df = pd\.DataFrame\(\)"
    replacement = """trades_df = result.get_trades_df()
    if trades_df.empty:
        logger.warning("No trades executed, metrics will be limited")"""
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    return content


def find_and_replace_engine(content: str) -> str:
    """Find and replace EventDrivenEngine/VectorizedEngine with TradeSimulator."""
    # This is complex, so we'll do a simple pattern match
    # Find: engine = EventDrivenEngine(...) or engine = VectorizedEngine(...)
    # Replace with full TradeSimulator pattern

    # Look for engine creation pattern
    engine_match = re.search(
        r"engine = (EventDrivenEngine|VectorizedEngine)\((.*?)\)\s*\n\s*result = engine\.run\(\)",
        content,
        flags=re.DOTALL,
    )

    if not engine_match:
        return content

    engine_type_old = engine_match.group(1)
    params_block = engine_match.group(2)

    # Extract parameters
    symbol_match = re.search(r"'symbol':\s*'(\w+)'", content)
    symbol = symbol_match.group(1) if symbol_match else "EURUSD"

    balance_match = re.search(r"initial_balance\s*=\s*([\d.]+)", params_block)
    balance = balance_match.group(1) if balance_match else "10000.0"

    commission_match = re.search(r"commission\s*=\s*([\d.]+)", params_block)
    commission = commission_match.group(1) if commission_match else "7.0"

    slippage_match = re.search(r"slippage_points\s*=\s*([\d]+)", params_block)
    slippage = slippage_match.group(1) if slippage_match else "0"

    # Determine engine type
    engine_type = "vectorised" if "Vectorized" in engine_type_old else "event_driven"

    # Build replacement
    replacement = f"""# Initialize strategy
    strategy.on_init()

    # Calculate signals
    data = strategy.on_bar(data)

    # Get MT5 client for symbol info
    mt5_client = get_mt5_client()

    # Setup simulator components
    account_info = AccountInfoSimulator(
        balance={balance},
        equity={balance},
        margin_free={balance},
    )
    symbol_info = SymbolInfoSimulator.from_mt5_symbol('{symbol}')
    symbol_info.symbol = '{symbol}'

    # Create simulator
    simulator = TradeSimulator(
        simulator_name="Backtest_{symbol}",
        mt5_client=mt5_client,
        account_info=account_info,
        symbols={{'{symbol}': symbol_info}},
    )

    # Run simulation
    simulator.run(
        data=data,
        strategy=strategy,
        symbol='{symbol}',
        volume=0.1,
        verbose=False,
        save_db=False,
        engine_type="{engine_type}",
        commission_per_contract={commission},
        slippage_points={slippage},
        start_date=backtest_start,
        end_date=backtest_end,
    )

    # Get results from simulator
    result = calculate_metrics_from_simulator(simulator)"""

    content = re.sub(
        r"engine = (EventDrivenEngine|VectorizedEngine)\(.*?\)\s*\n\s*result = engine\.run\(\)",
        replacement,
        content,
        flags=re.DOTALL,
    )

    return content


def add_cleanup(content: str) -> str:
    """Add MT5 client cleanup if not present."""
    if (
        "mt5_client.shutdown()" not in content
        and "mt5_client = get_mt5_client()" in content
    ):
        # Add before return or at end of main()
        content = re.sub(
            r"(\s+)return result",
            r"\n\1# Cleanup\n\1mt5_client.shutdown()\n\1\n\1return result",
            content,
        )
    return content


def update_file(file_path: Path) -> Tuple[bool, str]:
    """Update a single file with all fixes."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original = content

        # Apply all fixes
        content = fix_mt5_client_pattern(content)
        content = fix_trades_dataframe(content)
        content = find_and_replace_engine(content)
        content = add_cleanup(content)

        if content != original:
            file_path.write_text(content, encoding="utf-8")
            return True, f"Updated {file_path.name}"
        else:
            return False, f"No changes needed for {file_path.name}"

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False, f"Error updating {file_path.name}: {e}"


def main():
    """Execute main function."""
    # Find all files that still have EventDrivenEngine or VectorizedEngine
    backtest_dir = Path("tests/usage/backtest")
    files_to_update = []

    # Search for files with old patterns
    for py_file in backtest_dir.rglob("*.py"):
        if "metrics_utils" in str(py_file) or "__init__" in str(py_file):
            continue

        content = py_file.read_text(encoding="utf-8")
        if "EventDrivenEngine" in content or "VectorizedEngine" in content:
            files_to_update.append(py_file)

    print(f"Found {len(files_to_update)} files to update")
    print("=" * 70)

    updated = 0
    for file_path in sorted(files_to_update):
        success, message = update_file(file_path)
        if success:
            updated += 1
            print(f"[OK] {message}")
        else:
            print(f"[SKIP] {message}")

    print("=" * 70)
    print(f"Updated {updated}/{len(files_to_update)} files")


if __name__ == "__main__":
    main()
