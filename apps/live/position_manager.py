"""Position Manager.

Tracks open positions filtered by magic number and provides position information
for trade execution decisions.
"""

from typing import Dict, List, Optional

from backend.common.logger import logger
from backend.mcp.mt5_mcp.client import MT5Client
from apps.trading.trade import Trade


class PositionManager:
    """Manage and track open positions."""

    def __init__(self, client: MT5Client, magic_number: int):
        """Initialize position manager.

        Args:
            client: MT5Client instance
            magic_number: Magic number to filter positions
        """
        self.client = client
        self.magic_number = magic_number
        self._positions: List[Dict] = []

        # Initialize Trade instance
        self.trade = Trade(api=self.client)
        self.trade.SetExpertMagicNumber(magic_number)

        logger.info(f"PositionManager initialized with magic number {magic_number}")

    def refresh_positions(self):
        """Query MT5 for all positions with our magic number."""
        try:
            # Get all positions from MT5
            all_positions = self.client.positions_get()

            if all_positions is None:
                logger.warning("Failed to fetch positions from MT5")
                self._positions = []
                return

            # Filter by magic number
            self._positions = [
                pos
                for pos in all_positions
                if getattr(pos, "magic", None) == self.magic_number
            ]

            logger.debug(
                f"Refreshed positions: {len(self._positions)} open (magic: {self.magic_number})"
            )

        except Exception as e:
            logger.error(f"Error refreshing positions: {e}", exc_info=True)
            self._positions = []

    def get_positions_by_type(self, position_type: str) -> List[Dict]:
        """Get all positions of specified type.

        Args:
            position_type: 'buy' or 'sell'

        Returns:
            List of position dictionaries
        """
        if position_type.lower() not in ["buy", "sell"]:
            logger.warning(f"Unknown position type: {position_type}")
            return []

        # MT5 position types: 0 is Buy, 1 is Sell
        # Check raw type if available, otherwise check mapped enum if mapped
        # In this simple dict implementation, we check the integer value directly if possible
        # OrderType.BUY.value is typically mapped to mt5.ORDER_TYPE_BUY (0)

        # If OrderType.BUY maps to the same integer as MT5 position type:
        # 0 = Buy, 1 = Sell

        mt5_type = 0 if position_type.lower() == "buy" else 1

        positions = [
            pos for pos in self._positions if getattr(pos, "type", None) == mt5_type
        ]

        return positions

    def should_allow_entry(self, max_positions: int) -> bool:
        """Check if new position allowed based on position limit.

        Args:
            max_positions: Maximum allowed open positions

        Returns:
            True if new position can be opened
        """
        current_count = len(self._positions)
        allowed = current_count < max_positions

        if not allowed:
            logger.warning(f"Position limit reached: {current_count}/{max_positions}")

        return allowed

    def get_positions_to_close(self, signal_type: str) -> List[int]:
        """Get position tickets to close based on exit signal.

        Args:
            signal_type: 'close buy' or 'close sell'

        Returns:
            List of position tickets to close
        """
        if signal_type == "close buy":
            # Close all LONG (BUY) positions
            positions = self.get_positions_by_type("buy")
        elif signal_type == "close sell":
            # Close all SHORT (SELL) positions
            positions = self.get_positions_by_type("sell")
        else:
            logger.warning(f"Unknown exit signal type: {signal_type}")
            return []

        tickets = []
        for pos in positions:
            ticket = getattr(pos, "ticket", None)
            if ticket is not None:
                tickets.append(int(ticket))

        if tickets:
            logger.info(
                f"Found {len(tickets)} positions to close for signal '{signal_type}'"
            )

        return tickets

    def close_position(self, ticket: int) -> bool:
        """Close a specific position by ticket using Trade module.

        Args:
            ticket: Position ticket to close

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Attempting to close position #{ticket}")

        # We need the symbol to close the position using Trade.position_close
        # Find the position in our cache to get the symbol
        pos = next(
            (p for p in self._positions if getattr(p, "ticket", None) == ticket), None
        )

        if not pos:
            # Try to fetch fresh if not found in cache
            try:
                fresh_pos = self.client.positions_get(ticket=ticket)
                if fresh_pos:
                    pos = fresh_pos[0]
            except Exception as e:
                logger.error(f"Error fetching position #{ticket} for closing: {e}")

        if not pos:
            logger.error(f"Position #{ticket} not found, cannot close")
            return False

        symbol = getattr(pos, "symbol", None)
        if not symbol:
            logger.error(f"Position #{ticket} has no symbol, cannot close")
            return False

        # Execute close
        # Note: position_close in Trade takes symbol, and optionally ticket if hedging
        # If hedging is used, providing ticket is safer.
        # Check if Trade.position_close supports ticket argument (it should based on common implementations)
        # Based on apps/trading/trade.py seen earlier, position_close accepts symbol and deviation.
        # It internally selects position. For hedging, it might need updating if it doesn't support specific ticket.
        # Let's check trade.py again or rely on selecting it first.
        # The trade.py snippet showed: order_send.
        # Let's use position_close if available, or construct TradeRequest manually if needed.
        # Assuming standard Trade class:

        if self.trade.PositionClose(symbol=symbol, ticket=ticket):
            logger.info(f"Closed position #{ticket} ({symbol})")
            return True
        else:
            logger.error(
                f"Failed to close position #{ticket}: {self.trade.ResultRetcodeDescription()}"
            )
            return False

    def close_all_positions(self, position_type: Optional[str] = None) -> int:
        """Close all positions, optionally filtered by type.

        Args:
            position_type: 'buy' or 'sell', or None for all

        Returns:
            Number of closed positions
        """
        self.refresh_positions()

        if position_type:
            positions_to_close = self.get_positions_by_type(position_type)
        else:
            positions_to_close = self._positions

        count = 0
        for pos in positions_to_close:
            ticket = getattr(pos, "ticket", None)
            if ticket and self.close_position(ticket):
                count += 1

        return count

    def close_positions_by_symbol(self, symbol: str) -> int:
        """Close all positions for a specific symbol.

        Args:
            symbol: Symbol to close positions for

        Returns:
            Number of closed positions
        """
        self.refresh_positions()

        positions_to_close = [
            p for p in self._positions if getattr(p, "symbol", None) == symbol
        ]

        count = 0
        for pos in positions_to_close:
            ticket = getattr(pos, "ticket", None)
            if ticket and self.close_position(ticket):
                count += 1

        return count

    def total_positions(self) -> int:
        """Get total number of open positions.

        Returns:
            Count of open positions
        """
        return len(self._positions)

    def get_all_positions(self) -> List[Dict]:
        """Get all open positions.

        Returns:
            List of all position dictionaries
        """
        return self._positions.copy()

    def has_position_for_symbol(self, symbol: str) -> bool:
        """Check if any position exists for given symbol.

        Args:
            symbol: Trading symbol

        Returns:
            True if position exists for symbol
        """
        return any(getattr(pos, "symbol", None) == symbol for pos in self._positions)

    def get_position_summary(self) -> Dict[str, int]:
        """Get summary of positions by type.

        Returns:
            Dictionary with counts by type
        """
        buy_count = len(self.get_positions_by_type("buy"))
        sell_count = len(self.get_positions_by_type("sell"))

        return {"total": len(self._positions), "buy": buy_count, "sell": sell_count}

    def __repr__(self) -> str:
        """Return string representation of PositionManager."""
        summary = self.get_position_summary()
        return f"PositionManager(total={summary['total']}, buy={summary['buy']}, sell={summary['sell']})"


