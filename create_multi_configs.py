"""Create Multiple Configuration Files.

Helper script to generate config files for multiple symbols/strategies.
"""

import json


def create_config(
    symbol: str,
    magic_number: int,
    base_config_path: str = "config/live_trading_config.json",
):
    """Create a config file for a specific symbol.

    Args:
        symbol: Trading symbol (e.g., "EURUSD")
        magic_number: Unique magic number for this symbol
        base_config_path: Path to base config to copy from
    """
    # Load base config
    with open(base_config_path, "r") as f:
        config = json.load(f)

    # Modify for this symbol
    config["strategy"]["symbol"] = symbol
    config["trading"]["magic_number"] = magic_number
    config["state"]["file"] = f"live_trading_{symbol.lower()}_state.json"
    config["logging"]["dir"] = f"logs/live_trading_{symbol.lower()}"

    # Save new config
    output_path = f"config/live_{symbol.lower()}.json"
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Created: {output_path}")
    return output_path


def main():
    """Generate configs for multiple symbols."""
    symbols = [
        ("EURUSD", 123457),
        ("GBPUSD", 123458),
        ("USDJPY", 123459),
        ("AUDUSD", 123460),
        ("USDCAD", 123461),
    ]

    print("Creating configuration files...")
    print("=" * 80)

    created_files = []
    for symbol, magic_number in symbols:
        try:
            config_path = create_config(symbol, magic_number)
            created_files.append(config_path)
        except Exception as e:
            print(f"Error creating config for {symbol}: {e}")

    print("=" * 80)
    print(f"Created {len(created_files)} configuration file(s)")
    print("\nTo run multiple instances:")
    print("1. Edit run_multiple.py and add the config paths")
    print("2. Run: python run_multiple.py")
    print("\nOr run manually in separate terminals:")
    for config_path in created_files:
        print(f"  python -m apps.live.run --config {config_path}")


if __name__ == "__main__":
    main()
