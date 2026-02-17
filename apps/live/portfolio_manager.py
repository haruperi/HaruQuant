"""Portfolio Manager.

Portfolio-level risk management across multiple strategies and symbols.
Enforces portfolio-wide rules before allowing trade execution.
"""

from collections import defaultdict
from typing import Dict, List, Tuple

from apps.utils.logger import logger
from apps.mt5.client import MT5Client
from apps.trade import AccountInfo
from apps.utils.validate import OrderType


class PortfolioManager:
    """Manage portfolio-level risk across multiple strategies."""

    def __init__(
        self,
        client: MT5Client,
        account: AccountInfo,
        max_total_positions: int = 20,
        max_positions_per_symbol: int = 3,
        max_portfolio_risk_percent: float = 10.0,
        max_correlated_positions: int = 5,
    ):
        """Initialize portfolio manager.

        Args:
            client: MT5Client instance
            account: AccountInfo instance
            max_total_positions: Maximum total positions across all strategies
            max_positions_per_symbol: Maximum positions per symbol
            max_portfolio_risk_percent: Maximum portfolio risk as % of balance
            max_correlated_positions: Maximum positions in correlated pairs
        """
        self.client = client
        self.account = account
        self.max_total_positions = max_total_positions
        self.max_positions_per_symbol = max_positions_per_symbol
        self.max_portfolio_risk_percent = max_portfolio_risk_percent
        self.max_correlated_positions = max_correlated_positions

        # Track all positions across strategies
        self._all_positions: List[Dict] = []
        self._positions_by_symbol: Dict[str, List[Dict]] = defaultdict(list)
        self._positions_by_currency: Dict[str, int] = defaultdict(int)

        # Currency correlation groups (simplified)
        self._correlation_groups = {
            "EUR_group": ["EURUSD", "EURJPY", "EURGBP", "EURAUD", "EURCAD"],
            "GBP_group": ["GBPUSD", "GBPJPY", "EURGBP", "GBPAUD", "GBPCAD"],
            "JPY_group": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY"],
            "AUD_group": ["AUDUSD", "EURAUD", "GBPAUD", "AUDJPY", "AUDCAD"],
            "USD_group": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"],
            "GOLD_group": ["XAUUSD", "XAGUSD"],
        }

        logger.info(
            f"PortfolioManager initialized (max_total={max_total_positions}, "
            f"max_per_symbol={max_positions_per_symbol}, "
            f"max_risk={max_portfolio_risk_percent}%)"
        )

    def refresh_all_positions(self):
        """Refresh all positions from MT5."""
        try:
            # Get all positions
            positions = self.client.positions_get()

            if positions is None:
                positions = []

            self._all_positions = positions

            # Group by symbol
            self._positions_by_symbol.clear()
            for pos in positions:
                symbol = getattr(pos, "symbol", None)
                if symbol:
                    self._positions_by_symbol[symbol].append(pos)

            # Count by currency
            self._positions_by_currency.clear()
            for pos in positions:
                symbol = getattr(pos, "symbol", None)
                if symbol and len(symbol) >= 6:
                    # Extract base and quote currency (e.g., EURUSD -> EUR, USD)
                    base = symbol[:3]
                    quote = symbol[3:6]
                    self._positions_by_currency[base] += 1
                    self._positions_by_currency[quote] += 1

            logger.debug(f"Portfolio positions refreshed: {len(positions)} total")

        except Exception as e:
            logger.error(f"Error refreshing portfolio positions: {e}", exc_info=True)
            self._all_positions = []

    def can_open_position(
        self, symbol: str, strategy_name: str, volume: float, signal_type: str
    ) -> Tuple[bool, str]:
        """Check if position can be opened based on portfolio rules.

        Args:
            symbol: Trading symbol
            strategy_name: Name of strategy requesting position
            volume: Position volume
            signal_type: 'buy' or 'sell'

        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        try:
            # 1. Check total position limit
            total_positions = len(self._all_positions)
            if total_positions >= self.max_total_positions:
                reason = f"Portfolio position limit reached: {total_positions}/{self.max_total_positions}"
                logger.warning(f"[{strategy_name}] {reason}")
                return False, reason

            # 2. Check per-symbol limit
            symbol_positions = len(self._positions_by_symbol.get(symbol, []))
            if symbol_positions >= self.max_positions_per_symbol:
                reason = f"Symbol position limit reached for {symbol}: {symbol_positions}/{self.max_positions_per_symbol}"
                logger.warning(f"[{strategy_name}] {reason}")
                return False, reason

            # 3. Check portfolio risk
            passed, reason = self._check_portfolio_risk(symbol, volume)
            if not passed:
                logger.warning(f"[{strategy_name}] {reason}")
                return False, reason

            # 4. Check correlation exposure
            passed, reason = self._check_correlation_exposure(symbol)
            if not passed:
                logger.warning(f"[{strategy_name}] {reason}")
                return False, reason

            # 5. Check opposing positions on same symbol
            passed, reason = self._check_opposing_positions(symbol, signal_type)
            if not passed:
                logger.info(f"[{strategy_name}] {reason}")  # Info level, not warning
                # Allow opposing positions but log it
                # return False, reason

            logger.debug(f"[{strategy_name}] Portfolio checks passed for {symbol}")
            return True, "Portfolio checks passed"

        except Exception as e:
            reason = f"Error in portfolio checks: {e}"
            logger.error(reason, exc_info=True)
            return False, reason

    def _check_portfolio_risk(self, symbol: str, volume: float) -> Tuple[bool, str]:
        """Check if adding position would exceed portfolio risk limit.

        Args:
            symbol: Trading symbol
            volume: Position volume

        Returns:
            Tuple of (passed: bool, reason: str)
        """
        try:
            # Calculate current portfolio exposure
            balance = self.account.Balance()
            total_margin = self.account.Margin()

            if balance <= 0:
                return False, "Invalid account balance"

            # Current risk as % of balance
            # current_risk_percent = (total_margin / balance) * 100

            # Estimate additional risk from new position
            # This is simplified - you may want more sophisticated calculation
            estimated_new_margin = (
                total_margin * 1.05
            )  # Assume 5% increase per position

            new_risk_percent = (estimated_new_margin / balance) * 100

            if new_risk_percent > self.max_portfolio_risk_percent:
                reason = (
                    f"Portfolio risk limit exceeded: "
                    f"{new_risk_percent:.1f}% > {self.max_portfolio_risk_percent}%"
                )
                return False, reason

            return True, "Risk check passed"

        except Exception as e:
            return False, f"Risk check error: {e}"

    def _check_correlation_exposure(self, symbol: str) -> Tuple[bool, str]:
        """Check correlation exposure limits.

        Args:
            symbol: Trading symbol

        Returns:
            Tuple of (passed: bool, reason: str)
        """
        # Find which correlation group this symbol belongs to
        for group_name, symbols in self._correlation_groups.items():
            if symbol in symbols:
                # Count existing positions in this group
                group_positions = 0
                for sym in symbols:
                    group_positions += len(self._positions_by_symbol.get(sym, []))

                if group_positions >= self.max_correlated_positions:
                    reason = (
                        f"Correlation limit reached for {group_name}: "
                        f"{group_positions}/{self.max_correlated_positions}"
                    )
                    return False, reason

        return True, "Correlation check passed"

    def _check_opposing_positions(
        self, symbol: str, signal_type: str
    ) -> Tuple[bool, str]:
        """Check for opposing positions on same symbol.

        Args:
            symbol: Trading symbol
            signal_type: 'buy' or 'sell'

        Returns:
            Tuple of (passed: bool, reason: str)
        """
        existing_positions = self._positions_by_symbol.get(symbol, [])

        if not existing_positions:
            return True, "No existing positions"

        # Check for opposing direction
        for pos in existing_positions:
            pos_type = getattr(pos, "type", None)

            if signal_type == "buy" and pos_type == OrderType.SELL.value:
                reason = f"Warning: Opening BUY with existing SELL position on {symbol}"
                return True, reason  # Allow but warn

            elif signal_type == "sell" and pos_type == OrderType.BUY.value:
                reason = f"Warning: Opening SELL with existing BUY position on {symbol}"
                return True, reason  # Allow but warn

        return True, "No opposing positions"

    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary statistics.

        Returns:
            Dictionary with portfolio stats
        """
        try:
            balance = self.account.Balance()
            equity = self.account.Equity()
            margin = self.account.Margin()
            free_margin = self.account.FreeMargin()
            margin_level = self.account.MarginLevel()
            profit = self.account.Profit()

            # Count positions by direction
            buy_positions = sum(
                1
                for pos in self._all_positions
                if getattr(pos, "type", None) == OrderType.BUY.value
            )
            sell_positions = sum(
                1
                for pos in self._all_positions
                if getattr(pos, "type", None) == OrderType.SELL.value
            )

            # Top symbols by position count
            symbol_counts = {
                symbol: len(positions)
                for symbol, positions in self._positions_by_symbol.items()
            }
            top_symbols = sorted(
                symbol_counts.items(), key=lambda x: x[1], reverse=True
            )[:5]

            return {
                "total_positions": len(self._all_positions),
                "buy_positions": buy_positions,
                "sell_positions": sell_positions,
                "balance": balance,
                "equity": equity,
                "margin": margin,
                "free_margin": free_margin,
                "margin_level": margin_level,
                "profit": profit,
                "top_symbols": top_symbols,
                "currency_exposure": dict(self._positions_by_currency),
            }

        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {}

    def get_symbol_exposure(self, symbol: str) -> Dict:
        """Get exposure details for specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary with symbol exposure
        """
        positions = self._positions_by_symbol.get(symbol, [])

        total_volume = sum(getattr(pos, "volume", 0) for pos in positions)
        buy_volume = sum(
            getattr(pos, "volume", 0)
            for pos in positions
            if getattr(pos, "type", None) == OrderType.BUY.value
        )
        sell_volume = sum(
            getattr(pos, "volume", 0)
            for pos in positions
            if getattr(pos, "type", None) == OrderType.SELL.value
        )
        net_volume = buy_volume - sell_volume

        total_profit = sum(getattr(pos, "profit", 0) for pos in positions)

        return {
            "symbol": symbol,
            "position_count": len(positions),
            "total_volume": total_volume,
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "net_volume": net_volume,
            "total_profit": total_profit,
        }

    def __repr__(self) -> str:
        """Return string representation of PortfolioManager."""
        return (
            f"PortfolioManager(positions={len(self._all_positions)}, "
            f"symbols={len(self._positions_by_symbol)}, "
            f"max_total={self.max_total_positions})"
        )

