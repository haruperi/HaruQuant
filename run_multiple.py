"""Run Multiple Live Trading Instances.

Helper script to launch multiple live trading instances simultaneously.
Each instance runs in a separate process.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List


def run_multiple_strategies(config_files: List[str]):
    """Launch multiple live trading instances.

    Args:
        config_files: List of config file paths
    """
    processes: List[Dict[str, Any]] = []

    print("Starting multiple live trading instances...")
    print("=" * 80)

    for config_file in config_files:
        config_path = Path(config_file)

        if not config_path.exists():
            print(f"Warning: Config file not found: {config_file}")
            continue

        print(f"Launching: {config_file}")

        # Launch process
        process = subprocess.Popen(
            [sys.executable, "-m", "apps.live.run", "--config", config_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        processes.append({"config": config_file, "process": process})

    print("=" * 80)
    print(f"Started {len(processes)} instance(s)")
    print("Press Ctrl+C to stop all instances")
    print("=" * 80)

    try:
        # Wait for all processes
        for item in processes:
            stdout, stderr = item["process"].communicate()
            if stdout:
                print(f"\n[{item['config']}] STDOUT:\n{stdout}")
            if stderr:
                print(f"\n[{item['config']}] STDERR:\n{stderr}")

    except KeyboardInterrupt:
        print("\n\nShutting down all instances...")
        for item in processes:
            item["process"].terminate()

        # Wait for graceful shutdown
        for item in processes:
            item["process"].wait(timeout=10)

        print("All instances stopped")


if __name__ == "__main__":
    # Define your config files here
    configs = [
        "config/live_trading_config.json",  # XAUUSD
        # "config/live_eurusd.json",            # EURUSD
        # "config/live_gbpusd.json",            # GBPUSD
    ]

    run_multiple_strategies(configs)
