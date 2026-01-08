"""Safety Checks.

Comprehensive pre-trade validation to ensure safe trading conditions.
All checks must pass before any trade execution.
"""

from typing import Tuple

from apps.logger import logger
from apps.mt5.client import MT5Client
from apps.trading import AccountInfo, SymbolInfo


class SafetyChecker:
    """Perform safety checks before trade execution."""

    def __init__(
        self,
        client: MT5Client,
        account: AccountInfo,
        symbol_info: SymbolInfo,
        min_balance: float,
        min_margin_level: float,
    ):
        """Initialize safety checker.

        Args:
            client: MT5Client instance
            account: AccountInfo instance
            symbol_info: SymbolInfo instance
            min_balance: Minimum account balance required
            min_margin_level: Minimum margin level required (%)
        """
        self.client = client
        self.account = account
        self.symbol_info = symbol_info
        self.min_balance = min_balance
        self.min_margin_level = min_margin_level

        logger.info(
            f"SafetyChecker initialized (min_balance={min_balance}, min_margin_level={min_margin_level}%)"
        )

    def check_all(
        self,
        volume: float,
        position_count: int,
        daily_trades: int,
        max_positions: int,
        max_daily_trades: int,
    ) -> Tuple[bool, str]:
        """Run all safety checks.

        Args:
            volume: Trade volume to check
            position_count: Current number of open positions
            daily_trades: Number of trades executed today
            max_positions: Maximum allowed positions
            max_daily_trades: Maximum daily trades

        Returns:
            Tuple of (passed: bool, reason: str)
        """
        # 1. Check connection
        passed, reason = self.check_connection()
        if not passed:
            return False, reason

        # 2. Check account
        passed, reason = self.check_account()
        if not passed:
            return False, reason

        # 3. Check symbol
        passed, reason = self.check_symbol()
        if not passed:
            return False, reason

        # 4. Check volume
        passed, reason = self.check_volume(volume)
        if not passed:
            return False, reason

        # 5. Check limits
        passed, reason = self.check_limits(
            position_count, daily_trades, max_positions, max_daily_trades
        )
        if not passed:
            return False, reason

        logger.debug("All safety checks passed")
        return True, "All safety checks passed"

    def check_connection(self) -> Tuple[bool, str]:
        """Check MT5 connection is active.

        Returns:
            Tuple of (passed: bool, reason: str)
        """
        try:
            if not self.client.is_connected():
                reason = "MT5 connection lost"
                logger.error(reason)
                return False, reason

            return True, "Connection OK"

        except Exception as e:
            reason = f"Connection check failed: {e}"
            logger.error(reason)
            return False, reason

    def check_account(self) -> Tuple[bool, str]:
        """Check account status and margin.

        Returns:
            Tuple of (passed: bool, reason: str)
        """
        try:
            # Check if trading is allowed
            if not self.account.trade_allowed():
                reason = "Trading not allowed on this account"
                logger.error(reason)
                return False, reason

            # Check if expert trading is allowed
            if not self.account.trade_expert():
                reason = "Expert/automated trading not allowed"
                logger.error(reason)
                return False, reason

            # Check balance
            balance = self.account.balance()
            if balance < self.min_balance:
                reason = f"Balance too low: {balance} < {self.min_balance}"
                logger.error(reason)
                return False, reason

            # Check margin level
            margin_level = self.account.margin_level()
            if margin_level > 0 and margin_level < self.min_margin_level:
                reason = f"Margin level too low: {margin_level:.2f}% < {self.min_margin_level}%"
                logger.error(reason)
                return False, reason

            logger.debug(
                f"Account OK (balance={balance:.2f}, margin_level={margin_level:.2f}%)"
            )
            return True, "Account OK"

        except Exception as e:
            reason = f"Account check failed: {e}"
            logger.error(reason)
            return False, reason

    def check_symbol(self) -> Tuple[bool, str]:
        """Check symbol trading status.

        Returns:
            Tuple of (passed: bool, reason: str)
        """
        try:
            # Check if symbol trading is enabled
            trade_mode = self.symbol_info.trade_mode()
            if hasattr(trade_mode, "value"):
                trade_mode_value = trade_mode.value
            else:
                trade_mode_value = str(trade_mode)

            if "disabled" in trade_mode_value.lower():
                if hasattr(self.symbol_info, "name"):
                    symbol_name = str(self.symbol_info.name)
                else:
                    symbol_name = str(self.symbol_info)
                reason = f"Trading disabled for {symbol_name}"
                logger.error(reason)
                return False, reason

            # Check if symbol is selected (visible in Market Watch)
            # Note: This might not be critical for all brokers
            # If symbol is not visible, some brokers may not allow trading

            logger.debug(f"Symbol OK (trade_mode={trade_mode_value})")
            return True, "Symbol OK"

        except Exception as e:
            reason = f"Symbol check failed: {e}"
            logger.error(reason)
            return False, reason

    def check_volume(self, volume: float) -> Tuple[bool, str]:
        """Check if volume is within allowed limits.

        Args:
            volume: Trade volume to check

        Returns:
            Tuple of (passed: bool, reason: str)
        """
        try:
            min_vol = self.symbol_info.lots_min()
            max_vol = self.symbol_info.lots_max()
            step_vol = self.symbol_info.lots_step()

            # Check minimum
            if volume < min_vol:
                reason = f"Volume {volume} below minimum {min_vol}"
                logger.error(reason)
                return False, reason

            # Check maximum
            if volume > max_vol:
                reason = f"Volume {volume} above maximum {max_vol}"
                logger.error(reason)
                return False, reason

            # Check step (volume must be multiple of step)
            if step_vol > 0:
                steps = round((volume - min_vol) / step_vol)
                aligned = min_vol + steps * step_vol
                if abs(volume - aligned) > 1e-8:  # Allow small floating point errors
                    reason = f"Volume {volume} not aligned with step {step_vol}"
                    logger.error(reason)
                    return False, reason

            logger.debug(
                f"Volume OK ({volume} in range [{min_vol}, {max_vol}], step={step_vol})"
            )
            return True, "Volume OK"

        except Exception as e:
            reason = f"Volume check failed: {e}"
            logger.error(reason)
            return False, reason

    def check_limits(
        self,
        position_count: int,
        daily_trades: int,
        max_positions: int,
        max_daily_trades: int,
    ) -> Tuple[bool, str]:
        """Check position and trade count limits.

        Args:
            position_count: Current number of open positions
            daily_trades: Number of trades executed today
            max_positions: Maximum allowed positions
            max_daily_trades: Maximum daily trades

        Returns:
            Tuple of (passed: bool, reason: str)
        """
        try:
            # Check position limit
            if position_count >= max_positions:
                reason = f"Position limit reached: {position_count}/{max_positions}"
                logger.warning(reason)
                return False, reason

            # Check daily trade limit
            if daily_trades >= max_daily_trades:
                reason = f"Daily trade limit reached: {daily_trades}/{max_daily_trades}"
                logger.warning(reason)
                return False, reason

            logger.debug(
                f"Limits OK (positions={position_count}/{max_positions}, daily_trades={daily_trades}/{max_daily_trades})"
            )
            return True, "Limits OK"

        except Exception as e:
            reason = f"Limits check failed: {e}"
            logger.error(reason)
            return False, reason

    def __repr__(self) -> str:
        """Return string representation."""
        return f"SafetyChecker(min_balance={self.min_balance}, min_margin_level={self.min_margin_level}%)"
