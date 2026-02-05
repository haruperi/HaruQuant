"""
Script to fix strategy runner files that still use old EventDrivenEngine pattern.

This replaces the engine creation and run code with the new TradeSimulator pattern.
"""

import re
from pathlib import Path


def fix_mt5_client_usage(content: str) -> str:
    """Fix MT5Client initialization pattern."""
    # Pattern: with MT5Client(login=..., password=..., server=..., path=...) as client:
    old_pattern = r'def load_mt5_data\(symbol: str, timeframe: str, date_from: datetime, date_to: datetime\) -> pd\.DataFrame:\s*\n\s*creds = UserManager\(\)\.get_mt5_credentials\(\)\s*\n\s*with MT5Client\(login=creds\["login"\], password=creds\["password"\], server=creds\["server"\], path=creds\["path"\]\) as client:\s*\n\s*return client\.get_bars\(symbol=symbol, timeframe=timeframe, date_from=date_from, date_to=date_to\)'

    new_pattern = '''def get_mt5_client():
    """Get a connected MT5 client."""
    creds = UserManager().get_mt5_credentials()
    client = MT5Client()
    if not client.connect(creds["path"], creds["login"], creds["password"], creds["server"]):
        raise ConnectionError("Failed to connect to MT5")
    return client

def load_mt5_data(symbol: str, timeframe: str, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    client = get_mt5_client()
    try:
        df = client.get_bars(symbol=symbol, timeframe=timeframe, date_from=date_from, date_to=date_to)
        if df is None or df.empty:
            raise ValueError("No data retrieved from MT5")
        return df
    finally:
        client.shutdown()'''

    content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE)
    return content


def fix_engine_pattern(content: str) -> str:
    """Fix EventDrivenEngine pattern to use TradeSimulator."""
    # Match the pattern of:
    # strategy = SomeStrategy(params={'symbol': 'EURUSD'})
    # engine = EventDrivenEngine(...)
    # result = engine.run()

    # First, find the strategy variable name and symbol
    strategy_match = re.search(
        r'(\w+) = (\w+Strategy)\(params=\{[\'"]symbol[\'"]: [\'"](\w+)[\'"].*?\}\)',
        content,
    )
    if not strategy_match:
        return content

    strategy_var = strategy_match.group(1)
    symbol = strategy_match.group(3)

    # Find the engine creation block
    engine_pattern = (
        r"(\s+)"
        + re.escape(strategy_var)
        + r" = \w+Strategy\(params=\{.*?\}\)\s*\n\s+engine = EventDrivenEngine\((.*?)\)\s*\n\s+result = engine\.run\(\)"
    )

    def replacement(match):
        indent = match.group(1)
        engine_params = match.group(2)

        # Extract parameters from engine creation
        initial_balance = "10000.0"
        commission = "7.0"

        balance_match = re.search(r"initial_balance\s*=\s*([\d.]+)", engine_params)
        if balance_match:
            initial_balance = balance_match.group(1)

        comm_match = re.search(r"commission\s*=\s*([\d.]+)", engine_params)
        if comm_match:
            commission = comm_match.group(1)

        # Get backtest dates
        start_date_var = "backtest_start"
        end_date_var = "backtest_end"

        new_code = f"""{indent}{strategy_var} = {strategy_match.group(2)}(params={{'symbol': '{symbol}'}})

{indent}# Initialize strategy
{indent}{strategy_var}.on_init()

{indent}# Calculate signals
{indent}data = {strategy_var}.on_bar(data)

{indent}# Get MT5 client for symbol info
{indent}mt5_client = get_mt5_client()

{indent}# Setup simulator components
{indent}account_info = AccountInfoSimulator(
{indent}    balance={initial_balance},
{indent}    equity={initial_balance},
{indent}    margin_free={initial_balance},
{indent})
{indent}symbol_info = SymbolInfoSimulator.from_mt5_symbol('{symbol}')
{indent}symbol_info.symbol = '{symbol}'

{indent}# Create simulator
{indent}simulator = TradeSimulator(
{indent}    simulator_name="{strategy_match.group(2)}_Backtest",
{indent}    mt5_client=mt5_client,
{indent}    account_info=account_info,
{indent}    symbols={{'{symbol}': symbol_info}},
{indent})

{indent}# Run simulation
{indent}simulator.run(
{indent}    data=data,
{indent}    strategy={strategy_var},
{indent}    symbol='{symbol}',
{indent}    volume=0.1,
{indent}    verbose=False,
{indent}    save_db=False,
{indent}    engine_type="event_driven",
{indent}    commission_per_contract={commission},
{indent}    slippage_points=0,
{indent}    start_date={start_date_var},
{indent}    end_date={end_date_var},
{indent})

{indent}# Get results from simulator
{indent}result = calculate_metrics_from_simulator(simulator)"""

        return new_code

    content = re.sub(engine_pattern, replacement, content, flags=re.DOTALL)
    return content


def add_cleanup(content: str) -> str:
    """Add MT5 client cleanup before function end."""
    # Add shutdown before display_metrics if not already there
    if "mt5_client.shutdown()" not in content:
        content = content.replace(
            "    # Display metrics\n    display_metrics(result)",
            "    # Display metrics\n    display_metrics(result)\n\n    # Cleanup\n    mt5_client.shutdown()",
        )
        content = content.replace(
            "    display_metrics(result)",
            "    display_metrics(result)\n\n    # Cleanup\n    mt5_client.shutdown()",
        )
    return content


def fix_file(file_path: Path) -> bool:
    """Fix a single file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        original = content

        # Apply fixes
        content = fix_mt5_client_usage(content)
        content = fix_engine_pattern(content)
        content = add_cleanup(content)

        if content != original:
            file_path.write_text(content, encoding="utf-8")
            print(f"[OK] Fixed {file_path}")
            return True
        else:
            print(f"[SKIP] No changes for {file_path}")
            return False

    except Exception as e:
        print(f"[ERROR] Failed to fix {file_path}: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Execute main function."""
    # Find all strategy runner files
    strategy_runners = list(
        Path("tests/usage/backtest/01_strategies").glob("*_runner.py")
    )

    print(f"Found {len(strategy_runners)} strategy runner files")
    print("=" * 70)

    fixed_count = 0
    for runner in sorted(strategy_runners):
        if fix_file(runner):
            fixed_count += 1

    print("=" * 70)
    print(f"Fixed {fixed_count}/{len(strategy_runners)} files")


if __name__ == "__main__":
    main()
