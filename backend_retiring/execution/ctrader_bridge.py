"""cTrader bridge placeholder.

cTrader support is not implemented in the current codebase. This module exists
so Phase 2 has an explicit home, but all operational calls must fail closed.
"""


class CTraderBridgeUnavailable(RuntimeError):
    """Raised when cTrader execution is requested before support exists."""


def create_ctrader_bridge(*args, **kwargs):
    """Fail closed until a governed cTrader bridge is implemented."""

    raise CTraderBridgeUnavailable(
        "cTrader bridge is not implemented; live execution must use approved bridges only."
    )


__all__ = ["CTraderBridgeUnavailable", "create_ctrader_bridge"]
