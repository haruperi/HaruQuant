"""
Example usage of TradeErrorDescriptions.
"""

import os
import sys

# Add repo root to path for local imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from apps.mt5 import get_mt5_api
from apps.utils.error_description import TradeErrorDescriptions


def main():
    print("=" * 70)
    print("TradeErrorDescriptions Example")
    print("=" * 70)
    print()

    mt5 = get_mt5_api()
    print(
        TradeErrorDescriptions.trade_server_return_code_description(
            mt5.TRADE_RETCODE_DONE
        )
    )
    print(TradeErrorDescriptions.trade_server_return_code_description(999999))
    print(TradeErrorDescriptions.error_description(0))
    print(TradeErrorDescriptions.error_description(4704))
    print(TradeErrorDescriptions.error_description(65540))

    print("\n" + "=" * 70)
    print("Example Complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
