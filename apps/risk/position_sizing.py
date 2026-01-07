"""
Position Sizing Framework.

Dynamic position sizing based on various risk management methods.
Replaces hardcoded 0.1 lot sizing with intelligent, risk-based approaches.
"""

from typing import Any, Dict, Optional

from apps.logger import logger

from .result import BacktestResult


class PositionSizer:
    """
    Calculate position sizes based on various methods.

    All methods implement the same interface:
    - Input: account state, trade parameters, risk settings
    - Output: position size in lots

    Available methods:
    - fixed_lot: Always use fixed lot size (simplest)
    - milestone: Increase lot size at account balance milestones
    - fixed_risk: Risk fixed % of account per trade
    - kelly: Kelly Criterion optimal sizing
    - volatility: ATR-based volatility sizing
    - fixed_fractional: Fixed % of capital per position
    """

    def __init__(
        self, method: str = "fixed_risk", config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize position sizer.

        Args:
            method: Sizing method - "fixed_lot", "milestone", "fixed_risk", "kelly", "volatility", "fixed_fractional"
            config: Method-specific configuration
        """
        self.method = method
        self.config = config or {}

        # Validate method
        valid_methods = [
            "fixed_lot",
            "milestone",
            "fixed_risk",
            "kelly",
            "volatility",
            "fixed_fractional",
        ]
        if self.method not in valid_methods:
            raise ValueError(
                f"Unknown sizing method: {self.method}. Valid: {valid_methods}"
            )

        logger.info(f"PositionSizer initialized: method={method}, config={config}")

    def calculate_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: Optional[float] = None,
        symbol_info: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate position size based on configured method.

        Args:
            account_balance: Current account balance
            entry_price: Planned entry price
            stop_loss: Stop loss price (required for fixed_risk)
            symbol_info: SymbolInfo object with contract specs
            context: Additional data (ATR, win rate, etc.)

        Returns:
            Position size in lots
        """
        context = context or {}

        try:
            if self.method == "fixed_lot":
                size = self._fixed_lot_sizing()
            elif self.method == "milestone":
                size = self._milestone_sizing(account_balance)
            elif self.method == "fixed_risk":
                size = self._fixed_risk_sizing(
                    account_balance, entry_price, stop_loss, symbol_info
                )
            elif self.method == "kelly":
                size = self._kelly_criterion_sizing(
                    account_balance, entry_price, context
                )
            elif self.method == "volatility":
                size = self._volatility_based_sizing(
                    account_balance, entry_price, context, symbol_info
                )
            elif self.method == "fixed_fractional":
                size = self._fixed_fractional_sizing(
                    account_balance, entry_price, symbol_info
                )
            else:
                raise ValueError(f"Unknown sizing method: {self.method}")

            # Validate and adjust size
            if symbol_info:
                size = validate_position_size(size, symbol_info)

            return max(size, 0.01)  # Minimum 0.01 lots

        except Exception as e:
            logger.error(f"Position sizing error ({self.method}): {e}")
            return 0.1  # Fallback to default

    def _fixed_lot_sizing(self) -> float:
        """
        Use fixed lot size.

        Formula:
            position_size = lot_size

        Config:
            lot_size: float (default 0.1) - Fixed lot size to use

        This is the simplest method - just returns the configured lot size
        regardless of account balance, risk, or market conditions.
        """
        lot_size = float(self.config.get("lot_size", 0.1))

        logger.debug(f"Fixed lot: size={lot_size:.3f} lots")

        return lot_size

    def _milestone_sizing(self, account_balance: float) -> float:
        """
        Increase lot size at account balance milestones.

        Formula:
            milestones_reached = floor((account_balance - initial_balance) / milestone_amount)
            position_size = base_lot_size + (milestones_reached * lot_increment)

        Config:
            initial_balance: float (default 10000) - Starting account balance
            base_lot_size: float (default 0.1) - Starting lot size
            milestone_amount: float (default 3000) - Dollar increase required for next milestone
            lot_increment: float (default 0.2) - Lot size increase per milestone

        Example:
            Start at $10,000 with 0.1 lots
            Every $3,000 profit, increase by 0.2 lots
            $10,000 = 0.1 lots
            $13,000 = 0.3 lots (0.1 + 0.2)
            $16,000 = 0.5 lots (0.1 + 0.4)
            $19,000 = 0.7 lots (0.1 + 0.6)

        This method allows position sizing to grow with account while keeping
        increases discrete and controlled.
        """
        initial_balance = float(self.config.get("initial_balance", 10000.0))
        base_lot_size = float(self.config.get("base_lot_size", 0.1))
        milestone_amount = float(self.config.get("milestone_amount", 3000.0))
        lot_increment = float(self.config.get("lot_increment", 0.2))

        if account_balance <= 0 or milestone_amount <= 0:
            logger.warning(
                f"Invalid balance or milestone: balance={account_balance}, milestone={milestone_amount}"
            )
            return base_lot_size

        # Calculate how many milestones have been reached
        profit = max(0, account_balance - initial_balance)
        milestones_reached = int(profit / milestone_amount)

        # Calculate position size
        position_size = base_lot_size + (milestones_reached * lot_increment)

        logger.debug(
            f"Milestone: balance=${account_balance:.2f}, profit=${profit:.2f}, "
            f"milestones={milestones_reached}, size={position_size:.3f} lots"
        )

        return position_size

    def _fixed_risk_sizing(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: Optional[float],
        symbol_info: Any,
    ) -> float:
        """
        Risk fixed percentage of account per trade.

        Formula:
            risk_amount = account_balance * (risk_percent / 100)
            stop_distance = abs(entry_price - stop_loss)
            position_size = risk_amount / (stop_distance * point_value)

        Config:
            risk_percent: float (default 1.0) - Percentage of account to risk
        """
        risk_percent = float(self.config.get("risk_percent", 1.0))

        if stop_loss is None:
            logger.warning(
                "Fixed risk sizing requires stop_loss. Using default 0.1 lots."
            )
            return 0.1

        if account_balance <= 0:
            logger.warning(f"Invalid account balance: {account_balance}")
            return 0.01

        # Calculate risk amount
        risk_amount = account_balance * (risk_percent / 100)

        # Calculate stop distance in price
        stop_distance = abs(entry_price - stop_loss)

        if stop_distance == 0:
            logger.warning("Stop loss equals entry price. Using default 0.1 lots.")
            return 0.1

        # Get point value
        if symbol_info:
            try:
                contract_size = float(symbol_info.get_contract_size())
            except Exception:
                # Fallback for forex: 100,000 contract size
                contract_size = 100000.0
        else:
            # Default forex values
            contract_size = 100000.0

        # Calculate position size
        # risk_amount = stop_distance * position_size * point_value_per_lot
        # position_size = risk_amount / (stop_distance * point_value_per_lot)

        # For forex: point_value_per_lot = contract_size * point_size = 100000 * 0.0001 = 10
        position_size = risk_amount / (stop_distance * contract_size)

        logger.debug(
            f"Fixed risk: balance={account_balance}, risk={risk_percent}%, "
            f"risk_amt=${risk_amount:.2f}, stop_dist={stop_distance:.5f}, "
            f"size={position_size:.3f} lots"
        )

        return position_size

    def _kelly_criterion_sizing(
        self, account_balance: float, entry_price: float, context: Dict[str, Any]
    ) -> float:
        """
        Optimal sizing based on Kelly Criterion.

        Formula:
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            position_size = (account_balance * kelly_fraction) / (entry_price * contract_size)

        Config:
            kelly_fraction_limit: float (default 0.25) - Max Kelly fraction (for safety)
            win_rate: float - Fallback win rate if not in context
            avg_win: float - Fallback avg win
            avg_loss: float - Fallback avg loss

        Context should contain:
            win_rate: float (0-1)
            avg_win: float (absolute value)
            avg_loss: float (absolute value)
        """
        kelly_limit = float(self.config.get("kelly_fraction_limit", 0.25))

        # Get parameters from context or config
        win_rate_raw = context.get("win_rate", self.config.get("win_rate", 0.5))
        avg_win_raw = context.get("avg_win", self.config.get("avg_win", 100))
        avg_loss_raw = context.get("avg_loss", self.config.get("avg_loss", 50))

        win_rate = float(win_rate_raw) if win_rate_raw is not None else 0.5
        avg_win = float(avg_win_raw) if avg_win_raw is not None else 100.0
        avg_loss = float(avg_loss_raw) if avg_loss_raw is not None else 50.0

        # Ensure avg_loss is positive
        avg_loss = abs(avg_loss)

        if avg_win <= 0:
            logger.warning("Invalid avg_win for Kelly. Using default 0.1 lots.")
            return 0.1

        # Calculate Kelly fraction
        # kelly = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win

        # Apply limit for safety (half Kelly is common)
        kelly_fraction = max(0, min(kelly_fraction, kelly_limit))

        if kelly_fraction <= 0:
            logger.warning(
                f"Negative Kelly fraction: {kelly_fraction:.4f}. Using minimum size."
            )
            return 0.01

        # Get contract size
        contract_size = 100000  # Default forex

        # Calculate position size
        # position_value = account_balance * kelly_fraction
        # position_size = position_value / (entry_price * contract_size)
        position_size = (account_balance * kelly_fraction) / (
            entry_price * contract_size
        )

        logger.debug(
            f"Kelly: win_rate={win_rate:.2f}, avg_win={avg_win:.2f}, "
            f"avg_loss={avg_loss:.2f}, kelly={kelly_fraction:.4f}, "
            f"size={position_size:.3f} lots"
        )

        return position_size

    def _volatility_based_sizing(
        self,
        account_balance: float,
        entry_price: float,
        context: Dict[str, Any],
        symbol_info: Any,
    ) -> float:
        """
        Size inversely proportional to volatility (ATR).

        Formula:
            atr = context['atr']
            risk_amount = account_balance * (risk_percent / 100)
            volatility_units = risk_amount / (atr * contract_size)
            position_size = volatility_units

        Config:
            risk_percent: float (default 1.0)
            atr_multiplier: float (default 1.0) - Multiply ATR for conservative/aggressive

        Context should contain:
            atr: float - Average True Range value
        """
        risk_percent = float(self.config.get("risk_percent", 1.0))
        atr_multiplier = float(self.config.get("atr_multiplier", 1.0))

        # Get ATR from context
        atr_raw = context.get("atr")

        if atr_raw is None or atr_raw <= 0:
            logger.warning(
                "Invalid or missing ATR for volatility sizing. Using default 0.1 lots."
            )
            return 0.1

        # Apply multiplier to ATR (for conservative/aggressive sizing)
        atr = float(atr_raw)
        adjusted_atr = atr * atr_multiplier

        # Calculate risk amount
        risk_amount = account_balance * (risk_percent / 100)

        # Get contract size
        if symbol_info:
            try:
                contract_size = float(symbol_info.get_contract_size())
            except Exception:
                contract_size = 100000.0
        else:
            contract_size = 100000.0

        # Calculate position size
        # We want to risk a fixed amount based on ATR volatility
        # position_size = risk_amount / (atr * contract_size)
        position_size = risk_amount / (adjusted_atr * contract_size)

        logger.debug(
            f"Volatility: atr={atr:.5f}, multiplier={atr_multiplier}, "
            f"risk={risk_percent}%, size={position_size:.3f} lots"
        )

        return position_size

    def _fixed_fractional_sizing(
        self, account_balance: float, entry_price: float, symbol_info: Any
    ) -> float:
        """
        Use fixed percentage of capital.

        Formula:
            position_value = account_balance * (fraction / 100)
            position_size = position_value / (entry_price * contract_size)

        Config:
            fraction: float (default 2.0) - Percentage of account per position
        """
        fraction = float(self.config.get("fraction", 2.0))

        if account_balance <= 0:
            logger.warning(f"Invalid account balance: {account_balance}")
            return 0.01

        # Calculate position value
        position_value = account_balance * (fraction / 100)

        # Get contract size
        if symbol_info:
            try:
                contract_size = float(symbol_info.get_contract_size())
            except Exception:
                contract_size = 100000.0
        else:
            contract_size = 100000.0

        # Calculate position size
        position_size = position_value / (entry_price * contract_size)

        logger.debug(
            f"Fixed fractional: fraction={fraction}%, "
            f"value=${position_value:.2f}, size={position_size:.3f} lots"
        )

        return position_size


def validate_position_size(
    size: float, symbol_info: Any, max_size: Optional[float] = None
) -> float:
    """
    Validate and adjust position size to meet constraints.

    - Round to lot step
    - Enforce min/max lot size
    - Apply optional max size limit

    Args:
        size: Calculated position size
        symbol_info: SymbolInfo object with constraints
        max_size: Optional maximum size override

    Returns:
        Validated position size
    """
    try:
        min_lot = symbol_info.get_volume_min()
        max_lot = symbol_info.get_volume_max()
        lot_step = symbol_info.get_volume_step()
    except Exception:
        # Fallback defaults for forex
        min_lot = 0.01
        max_lot = 100.0
        lot_step = 0.01

    # Apply max size override if provided
    if max_size is not None:
        max_lot = min(max_lot, max_size)

    # Round to lot step
    size = round(size / lot_step) * lot_step

    # Enforce min/max
    size = max(min_lot, min(size, max_lot))

    return size


def estimate_kelly_parameters(result: BacktestResult) -> Dict[str, float]:
    """
    Estimate Kelly Criterion parameters from backtest result.

    Useful for configuring Kelly sizing based on historical performance.

    Args:
        result: BacktestResult object

    Returns:
        {
            'win_rate': float (0-1),
            'avg_win': float (absolute value),
            'avg_loss': float (absolute value),
            'kelly_fraction': float (calculated Kelly %)
        }
    """
    trades_df = result.get_trades_df()

    if len(trades_df) == 0:
        logger.warning("No trades in result for Kelly estimation")
        return {
            "win_rate": 0.5,
            "avg_win": 100.0,
            "avg_loss": 50.0,
            "kelly_fraction": 0.0,
        }

    # Calculate win rate
    winning_trades = trades_df[trades_df["pnl"] > 0]
    losing_trades = trades_df[trades_df["pnl"] <= 0]

    win_rate = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0.5

    # Calculate average win/loss (absolute values)
    avg_win = winning_trades["pnl"].mean() if len(winning_trades) > 0 else 0
    avg_loss = abs(losing_trades["pnl"].mean()) if len(losing_trades) > 0 else 0

    # Calculate Kelly fraction
    if avg_win > 0:
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    else:
        kelly_fraction = 0.0

    kelly_fraction = max(0, kelly_fraction)  # Ensure non-negative

    logger.info(
        f"Kelly estimation: win_rate={win_rate:.3f}, avg_win={avg_win:.2f}, "
        f"avg_loss={avg_loss:.2f}, kelly={kelly_fraction:.4f}"
    )

    return {
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "kelly_fraction": kelly_fraction,
    }
