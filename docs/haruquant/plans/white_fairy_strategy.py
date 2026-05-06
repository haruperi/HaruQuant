"""
White Fairy Strategy.

Converted from the MT5 Expert Advisor "White Fairy EA.mq5" into the
provided TemplateStrategy structure.

Important conversion notes:
- MT5 chart/UI configuration is intentionally omitted because it has no trading effect.
- The EA runs only on a new bar. In this Python strategy, the backtest/live engine
  should call get_signal() once per completed bar index.
- RSI signals are calculated in on_bar() using previous closed bars, matching the
  MT5 logic that reads RSIBuffer[1] and RSIBuffer[2] after a new bar starts.
- Stateful basket management is handled in get_signal(), because corrective averaging
  and pyramiding depend on the current basket state and previous order prices.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from services.utils.logger import logger
from services.strategy import BaseStrategy
from services.strategy.base import SignalDict


class TemplateStrategy(BaseStrategy):
    """
    White Fairy Strategy.

    Strategy summary:
    - Uses RSI on the selected applied price, usually close.
    - Opens a first buy when RSI crosses upward out of oversold.
    - Opens a first sell when RSI crosses downward out of overbought.
    - Adds corrective averaging trades when a fresh RSI signal appears and price has
      moved against the current basket by CTradeDistance.
    - Adds pyramid trades when price moves in favor of the basket by PTradeDistance.
    - Corrective averaging sets take profit at the simple average entry price.
    - Pyramiding reduces the next pyramid lot and moves basket stop loss behind price.

    Parameters via params dict:
        symbol: Trading symbol. Default: "EURUSD".
        timeframe: Trading timeframe. Default: "M5".

        rsi_period: RSI period. MT5 default: 14.
        rsi_price_column: DataFrame column used for RSI. MT5 default PRICE_CLOSE -> "close".
        os_level: Oversold level. MT5 default: 30.
        ob_level: Overbought level. MT5 default: 70.

        balance_increase: Balance step used in lot formula. MT5 default: 2000.
        volume_increase: Lot increase per balance step. MT5 default: 0.01.
        account_balance: Balance used for lot sizing in this signal-only conversion.
                         If omitted, initial_balance is used, then 10000.
        volume_min: Symbol minimum volume. Default: 0.01.
        volume_max: Symbol maximum volume. Default: 100.0.

        c_trade_distance: Corrective averaging distance in pips. MT5 default: 10.
        p_trade_distance: Pyramiding distance in pips. MT5 default: 10.
        lot_divisor: Divides pyramid lot after every pyramid entry. MT5 default: 2.
        sl_displacement: Stop displacement in pips. MT5 default: 5.

        point: Symbol point size. EURUSD 5-digit default: 0.00001.
        pip_multiplier: MT5 code multiplies pip-style inputs by 10 * point. Default: 10.
        digits: Symbol price digits. EURUSD 5-digit default: 5.

        buy_price_column: Optional DataFrame column for buy execution price.
                          If missing, uses ask_open, then ask, then open.
        sell_price_column: Optional DataFrame column for sell execution price.
                           If missing, uses bid_open, then bid, then open.
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy parameters and runtime state.

        The MT5 EA stores several global variables such as next buy price, next sell
        price, current pyramid lot, and corrective averaging lot. In Python these are
        stored as instance attributes so get_signal() can preserve state from bar to bar.
        """
        super().__init__(params)

        # Core identity/configuration values from the EA inputs.
        self.symbol = self.params.get("symbol", "EURUSD")
        self.timeframe = self.params.get("timeframe", "M5")
        self.ea_magic = int(self.params.get("ea_magic", 763562536))
        self.max_slippage = int(self.params.get("max_slippage", 1))

        # RSI settings from the EA inputs.
        self.rsi_period = int(self.params.get("rsi_period", 14))
        self.rsi_price_column = self.params.get("rsi_price_column", "close")
        self.os_level = float(self.params.get("os_level", 30))
        self.ob_level = float(self.params.get("ob_level", 70))

        # Lot sizing settings from the EA inputs.
        self.balance_increase = float(self.params.get("balance_increase", 2000))
        self.volume_increase = float(self.params.get("volume_increase", 0.01))
        self.account_balance = float(
            self.params.get(
                "account_balance",
                self.params.get("initial_balance", 10000.0),
            )
        )
        self.volume_min = float(self.params.get("volume_min", 0.01))
        self.volume_max = float(self.params.get("volume_max", 100.0))

        # Trade management settings from the EA inputs.
        self.c_trade_distance = float(self.params.get("c_trade_distance", 10))
        self.p_trade_distance = float(self.params.get("p_trade_distance", 10))
        self.lot_divisor = float(self.params.get("lot_divisor", 2))
        self.sl_displacement = float(self.params.get("sl_displacement", 5))

        # Symbol precision settings. The EA calculates distance as input * 10 * point.
        self.point = float(self.params.get("point", 0.00001))
        self.pip_multiplier = float(self.params.get("pip_multiplier", 10))
        self.digits = int(self.params.get("digits", 5))

        # Converted point distances used by corrective averaging, pyramiding, and SL moves.
        self.c_trade_distance_point = self.c_trade_distance * self.pip_multiplier * self.point
        self.p_trade_distance_point = self.p_trade_distance * self.pip_multiplier * self.point
        self.sl_displacement_point = self.sl_displacement * self.pip_multiplier * self.point

        # Optional execution price columns. These allow spread-aware data if available.
        self.buy_price_column = self.params.get("buy_price_column")
        self.sell_price_column = self.params.get("sell_price_column")

        # Validate input values before the engine starts.
        if self.rsi_period <= 0:
            raise ValueError(f"rsi_period must be positive, got {self.rsi_period}")
        if self.balance_increase <= 0:
            raise ValueError(f"balance_increase must be positive, got {self.balance_increase}")
        if self.volume_increase <= 0:
            raise ValueError(f"volume_increase must be positive, got {self.volume_increase}")
        if self.lot_divisor <= 0:
            raise ValueError(f"lot_divisor must be positive, got {self.lot_divisor}")
        if self.point <= 0:
            raise ValueError(f"point must be positive, got {self.point}")

        # Runtime basket state. This mirrors the EA globals such as PBuyLot, CABuyLot,
        # CNextBuyPrice, PNextBuyPrice, and their sell-side equivalents.
        self._reset_runtime_state()

    def _reset_runtime_state(self) -> None:
        """
        Reset all runtime trading state.

        This is separated from __init__ so on_init() can reset the strategy before a
        new backtest/live run starts. It keeps buy and sell baskets separate, matching
        the MT5 hedging-style logic where buys and sells are counted independently.
        """
        self.buy_positions: List[Dict[str, float]] = []
        self.sell_positions: List[Dict[str, float]] = []

        self.ca_buy_lot: Optional[float] = None
        self.ca_sell_lot: Optional[float] = None
        self.p_buy_lot: Optional[float] = None
        self.p_sell_lot: Optional[float] = None

        self.c_next_buy_price: Optional[float] = None
        self.c_next_sell_price: Optional[float] = None
        self.p_next_buy_price: Optional[float] = None
        self.p_next_sell_price: Optional[float] = None

        self.last_buy_price: Optional[float] = None
        self.last_sell_price: Optional[float] = None

        # Prevent duplicate processing if get_signal() is called twice for the same bar.
        self._processed_bar_keys = set()
        self._last_processed_index: Optional[int] = None

    def on_init(self) -> None:
        """
        Initialize strategy before a run.

        The EA's OnInit() configures chart colors and CTrade settings. Chart settings are
        skipped here. We only reset state and log the trading parameters that affect logic.
        """
        self._reset_runtime_state()
        logger.info(
            "White Fairy Strategy initialized: symbol=%s timeframe=%s rsi_period=%s "
            "os=%s ob=%s c_distance=%s p_distance=%s lot_divisor=%s",
            self.symbol,
            self.timeframe,
            self.rsi_period,
            self.os_level,
            self.ob_level,
            self.c_trade_distance,
            self.p_trade_distance,
            self.lot_divisor,
        )

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate vectorized RSI conditions and initialize signal columns.

        MT5 uses CopyBuffer(RSIHandle, 0, 0, 4, RSIBuffer), then checks:
        - Buy:  RSIBuffer[1] >= OSLevel and RSIBuffer[2] < OSLevel
        - Sell: RSIBuffer[1] <= OBLevel and RSIBuffer[2] > OBLevel

        Because RSIBuffer[1] is the last closed bar and RSIBuffer[2] is the bar before it,
        this Python version shifts RSI by 1 and 2 bars before creating signals. That means
        the current row can trade at the current open without using the current close.
        """
        # Work on a copy so the caller's original DataFrame is not mutated unexpectedly.
        data = data.copy()

        # Validate the minimum data columns required by this strategy.
        required_columns = {"open", self.rsi_price_column}
        missing_columns = required_columns.difference(data.columns)
        if missing_columns:
            raise ValueError(f"Missing required data columns: {sorted(missing_columns)}")

        # Resolve execution price columns. MT5 uses ASK for buys and BID for sells.
        # If spread-aware columns are unavailable, the strategy falls back to open.
        buy_price_col = self._resolve_price_column(
            data=data,
            explicit_column=self.buy_price_column,
            fallback_columns=("ask_open", "ask", "open"),
        )
        sell_price_col = self._resolve_price_column(
            data=data,
            explicit_column=self.sell_price_column,
            fallback_columns=("bid_open", "bid", "open"),
        )

        # Calculate RSI using Wilder-style smoothing, close to MT5's iRSI behavior.
        rsi_col = f"rsi_{self.rsi_period}"
        data[rsi_col] = self._calculate_rsi(data[self.rsi_price_column], self.rsi_period)

        # Shift RSI so the signal at this row only uses completed bars.
        data["rsi_closed_1"] = data[rsi_col].shift(1)
        data["rsi_closed_2"] = data[rsi_col].shift(2)

        # Vectorized RSI signal conditions from the EA.
        data["rsi_buy_signal"] = (data["rsi_closed_1"] >= self.os_level) & (
            data["rsi_closed_2"] < self.os_level
        )
        data["rsi_sell_signal"] = (data["rsi_closed_1"] <= self.ob_level) & (
            data["rsi_closed_2"] > self.ob_level
        )

        # Store execution prices used by get_signal(). These are separate because buys
        # should use ask-like prices and sells should use bid-like prices when available.
        data["buy_price"] = data[buy_price_col]
        data["sell_price"] = data[sell_price_col]

        # Initialize the standard template signal columns.
        data["entry_signal"] = 0
        data["exit_signal"] = 0
        data["pending_signal"] = 0
        data["cancel_pending_signal"] = 0
        data["price"] = float("nan")
        data["signal_reason"] = ""

        # Mark base RSI entries. Corrective averaging also uses the same RSI signal,
        # but whether it is a first entry or an averaging entry is decided in get_signal().
        buy_mask = data["rsi_buy_signal"]
        sell_mask = data["rsi_sell_signal"]

        data.loc[buy_mask, "entry_signal"] = 1
        data.loc[buy_mask, "price"] = data.loc[buy_mask, "buy_price"]
        data.loc[buy_mask, "signal_reason"] = "RSI crossed upward out of oversold"

        data.loc[sell_mask, "entry_signal"] = -1
        data.loc[sell_mask, "price"] = data.loc[sell_mask, "sell_price"]
        data.loc[sell_mask, "signal_reason"] = "RSI crossed downward out of overbought"

        return data

    def get_signal(self, data: pd.DataFrame, index: int) -> Optional[SignalDict]:
        """
        Parse one bar into a standardized SignalDict.

        This method also applies the EA's stateful basket rules:
        1. First buy/sell entries from RSI crosses.
        2. Corrective averaging entries on repeated RSI signals at worse prices.
        3. Pyramiding entries when price moves in favor by PTradeDistance.

        A standard SignalDict can carry one primary order. If more than one EA action
        happens on the same bar, the first action is returned as the main signal and the
        rest are included under "additional_actions" for engines that support batching.
        """
        # If an engine restarts iteration using the same strategy object, reset state.
        if self._last_processed_index is not None and index < self._last_processed_index:
            self._reset_runtime_state()

        bar = data.iloc[index]
        bar_key = (index, bar.name)

        # Match the EA's NewBar() behavior by processing each bar only once.
        if bar_key in self._processed_bar_keys:
            return None

        self._processed_bar_keys.add(bar_key)
        self._last_processed_index = index

        # Extract vectorized RSI signals produced by on_bar().
        buy_signal = bool(bar.get("rsi_buy_signal", False))
        sell_signal = bool(bar.get("rsi_sell_signal", False))

        # Extract execution prices. Fallback to the template price/open/close if needed.
        buy_price = self._safe_price(bar, preferred_column="buy_price")
        sell_price = self._safe_price(bar, preferred_column="sell_price")

        actions: List[SignalDict] = []

        # The sequence below follows the MT5 OnTick() call order:
        # Buy(); Sell(); CBuy(); CSell(); PBuy(); PSell();
        if buy_signal and self._num_buys() == 0:
            actions.append(self._open_first_buy(price=buy_price, time=bar.name))

        if sell_signal and self._num_sells() == 0:
            actions.append(self._open_first_sell(price=sell_price, time=bar.name))

        if buy_signal and self._num_buys() > 0:
            c_buy_action = self._try_corrective_buy(price=buy_price, time=bar.name)
            if c_buy_action is not None:
                actions.append(c_buy_action)

        if sell_signal and self._num_sells() > 0:
            c_sell_action = self._try_corrective_sell(price=sell_price, time=bar.name)
            if c_sell_action is not None:
                actions.append(c_sell_action)

        if self._num_buys() > 0:
            p_buy_action = self._try_pyramid_buy(price=buy_price, time=bar.name)
            if p_buy_action is not None:
                actions.append(p_buy_action)

        if self._num_sells() > 0:
            p_sell_action = self._try_pyramid_sell(price=sell_price, time=bar.name)
            if p_sell_action is not None:
                actions.append(p_sell_action)

        # No trade action on this bar.
        if not actions:
            return None

        # Return the first action as the main SignalDict. Keep any extra actions so a
        # richer execution engine can place all orders from the same bar if desired.
        primary_action = actions[0]
        if len(actions) > 1:
            primary_action["additional_actions"] = actions[1:]  # type: ignore[index]

        return primary_action

    @staticmethod
    def _resolve_price_column(
        data: pd.DataFrame,
        explicit_column: Optional[str],
        fallback_columns: tuple,
    ) -> str:
        """
        Pick the best available price column.

        Args:
            data: Market data DataFrame.
            explicit_column: User-selected column name, if provided.
            fallback_columns: Ordered columns to try when explicit_column is absent.

        Returns:
            Column name to use for execution price.
        """
        if explicit_column:
            if explicit_column not in data.columns:
                raise ValueError(f"Configured price column not found: {explicit_column}")
            return explicit_column

        for column in fallback_columns:
            if column in data.columns:
                return column

        raise ValueError(f"None of the fallback price columns exist: {fallback_columns}")

    @staticmethod
    def _calculate_rsi(series: pd.Series, period: int) -> pd.Series:
        """
        Calculate RSI with Wilder-style exponential smoothing.

        MT5's iRSI uses a Wilder-style RSI. Pandas ewm(alpha=1/period) is the closest
        vectorized equivalent and works well for strategy signal parity after warm-up.
        """
        delta = series.diff()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)

        avg_gain = gains.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
        avg_loss = losses.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))

        # Handle edge cases explicitly so flat or one-sided markets do not create NaNs
        # after the warm-up period.
        rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100)
        rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0)
        rsi = rsi.mask((avg_gain == 0) & (avg_loss == 0), 50)

        return rsi

    def _safe_price(self, bar: pd.Series, preferred_column: str) -> float:
        """
        Read a price from the bar with safe fallbacks.

        The template normally uses the 'price' column, but this strategy uses separate
        buy_price and sell_price columns to match ASK/BID behavior when available.
        """
        price = bar.get(preferred_column)
        if price is None or pd.isna(price):
            price = bar.get("price")
        if price is None or pd.isna(price):
            price = bar.get("open")
        if price is None or pd.isna(price):
            price = bar.get("close")

        return self._normalize_price(float(price))

    def _normalize_price(self, value: float) -> float:
        """
        Match MT5 NormalizeDouble(value, MyDigits) for prices.
        """
        return self._round_decimal(value=value, decimals=self.digits)

    def _normalize_lot(self, value: float) -> float:
        """
        Match MT5 NormalizeDouble(value, 2) for lots.
        """
        return self._round_decimal(value=value, decimals=2)

    @staticmethod
    def _round_decimal(value: float, decimals: int) -> float:
        """
        Round like MT5 NormalizeDouble using decimal half-up rounding.
        """
        quant = Decimal("1").scaleb(-decimals)
        return float(Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP))

    def _lot_size(self) -> float:
        """
        Calculate first-entry lot size using the EA formula.

        EA formula:
            Lot = NormalizeDouble(VolumeIncrease * AccountBalance / BalanceIncrease, 2)
            Lot is then clamped between symbol min and symbol max.
        """
        raw_lot = self.volume_increase * self.account_balance / self.balance_increase
        lot = self._normalize_lot(raw_lot)
        lot = min(lot, self.volume_max)
        lot = max(lot, self.volume_min)
        return self._normalize_lot(lot)

    def _num_buys(self) -> int:
        """
        Count open buy positions in the internal basket state.
        """
        return len(self.buy_positions)

    def _num_sells(self) -> int:
        """
        Count open sell positions in the internal basket state.
        """
        return len(self.sell_positions)

    def _avg_buy_price(self) -> Optional[float]:
        """
        Calculate the EA's simple average buy entry price.

        The original EA averages open prices directly and does not lot-weight them.
        This method intentionally preserves that behavior.
        """
        if not self.buy_positions:
            return None
        avg = sum(position["price"] for position in self.buy_positions) / len(self.buy_positions)
        return self._normalize_price(avg)

    def _avg_sell_price(self) -> Optional[float]:
        """
        Calculate the EA's simple average sell entry price.

        The original EA averages open prices directly and does not lot-weight them.
        This method intentionally preserves that behavior.
        """
        if not self.sell_positions:
            return None
        avg = sum(position["price"] for position in self.sell_positions) / len(self.sell_positions)
        return self._normalize_price(avg)

    def _open_first_buy(self, price: float, time: Any) -> SignalDict:
        """
        Open the first buy basket trade and initialize buy-side thresholds.
        """
        lot = self._lot_size()

        self.buy_positions.append({"price": price, "lot": lot})
        self.ca_buy_lot = lot
        self.p_buy_lot = self._normalize_lot(lot / self.lot_divisor)
        self.c_next_buy_price = self._normalize_price(price - self.c_trade_distance_point)
        self.p_next_buy_price = self._normalize_price(price + self.p_trade_distance_point)

        return self._build_signal(
            entry_signal=1,
            price=price,
            time=time,
            volume=lot,
            reason="FirstBuy: RSI crossed upward out of oversold and no buy basket exists",
            comment="FirstBuy",
            action="first_buy",
        )

    def _open_first_sell(self, price: float, time: Any) -> SignalDict:
        """
        Open the first sell basket trade and initialize sell-side thresholds.
        """
        lot = self._lot_size()

        self.sell_positions.append({"price": price, "lot": lot})
        self.ca_sell_lot = lot
        self.p_sell_lot = self._normalize_lot(lot / self.lot_divisor)
        self.c_next_sell_price = self._normalize_price(price + self.c_trade_distance_point)
        self.p_next_sell_price = self._normalize_price(price - self.p_trade_distance_point)

        return self._build_signal(
            entry_signal=-1,
            price=price,
            time=time,
            volume=lot,
            reason="FirstSell: RSI crossed downward out of overbought and no sell basket exists",
            comment="FirstSell",
            action="first_sell",
        )

    def _try_corrective_buy(self, price: float, time: Any) -> Optional[SignalDict]:
        """
        Add a corrective averaging buy if price is at or below CNextBuyPrice.
        """
        if self.ca_buy_lot is None or self.c_next_buy_price is None:
            return None

        # EA condition: if ASK > CNextBuyPrice, return.
        if price > self.c_next_buy_price:
            return None

        lot = self.ca_buy_lot
        self.buy_positions.append({"price": price, "lot": lot})
        self.c_next_buy_price = self._normalize_price(price - self.c_trade_distance_point)

        # Corrective averaging sets TP on all buy positions to the simple average price.
        take_profit = self._avg_buy_price()
        for position in self.buy_positions:
            position["take_profit"] = take_profit
            position["stop_loss"] = None

        return self._build_signal(
            entry_signal=1,
            price=price,
            time=time,
            volume=lot,
            reason="C.Averaging Buy: RSI buy signal repeated at corrective distance",
            comment="C.Averaging Buy",
            action="corrective_buy",
            take_profit=take_profit,
            modify_existing_positions=True,
        )

    def _try_corrective_sell(self, price: float, time: Any) -> Optional[SignalDict]:
        """
        Add a corrective averaging sell if price is at or above CNextSellPrice.
        """
        if self.ca_sell_lot is None or self.c_next_sell_price is None:
            return None

        # EA condition: if BID < CNextSellPrice, return.
        if price < self.c_next_sell_price:
            return None

        lot = self.ca_sell_lot
        self.sell_positions.append({"price": price, "lot": lot})
        self.c_next_sell_price = self._normalize_price(price + self.c_trade_distance_point)

        # Corrective averaging sets TP on all sell positions to the simple average price.
        take_profit = self._avg_sell_price()
        for position in self.sell_positions:
            position["take_profit"] = take_profit
            position["stop_loss"] = None

        return self._build_signal(
            entry_signal=-1,
            price=price,
            time=time,
            volume=lot,
            reason="C.Averaging Sell: RSI sell signal repeated at corrective distance",
            comment="C.Averaging Sell",
            action="corrective_sell",
            take_profit=take_profit,
            modify_existing_positions=True,
        )

    def _try_pyramid_buy(self, price: float, time: Any) -> Optional[SignalDict]:
        """
        Add a pyramid buy if price is at or above PNextBuyPrice.
        """
        if self.p_buy_lot is None or self.p_next_buy_price is None:
            return None

        # EA condition: if ASK < PNextBuyPrice, return.
        if price < self.p_next_buy_price:
            return None

        lot = self.p_buy_lot
        self.buy_positions.append({"price": price, "lot": lot})

        self.last_buy_price = self._normalize_price(price - self.p_trade_distance_point)
        self.p_next_buy_price = self._normalize_price(price + self.p_trade_distance_point)
        self.p_buy_lot = self._normalize_lot(lot / self.lot_divisor)

        # Pyramiding modifies all buy positions to the new stop loss and clears TP.
        stop_loss = self._normalize_price(self.last_buy_price + self.sl_displacement_point)
        for position in self.buy_positions:
            position["stop_loss"] = stop_loss
            position["take_profit"] = None

        return self._build_signal(
            entry_signal=1,
            price=price,
            time=time,
            volume=lot,
            reason="Pyramid Buy: price advanced by pyramid distance",
            comment="Pyrammid Buy",
            action="pyramid_buy",
            stop_loss=stop_loss,
            modify_existing_positions=True,
            clear_take_profit=True,
        )

    def _try_pyramid_sell(self, price: float, time: Any) -> Optional[SignalDict]:
        """
        Add a pyramid sell if price is at or below PNextSellPrice.
        """
        if self.p_sell_lot is None or self.p_next_sell_price is None:
            return None

        # EA condition: if BID > PNextSellPrice, return.
        if price > self.p_next_sell_price:
            return None

        lot = self.p_sell_lot
        self.sell_positions.append({"price": price, "lot": lot})

        self.last_sell_price = self._normalize_price(price + self.p_trade_distance_point)
        self.p_next_sell_price = self._normalize_price(price - self.p_trade_distance_point)
        self.p_sell_lot = self._normalize_lot(lot / self.lot_divisor)

        # Pyramiding modifies all sell positions to the new stop loss and clears TP.
        stop_loss = self._normalize_price(self.last_sell_price - self.sl_displacement_point)
        for position in self.sell_positions:
            position["stop_loss"] = stop_loss
            position["take_profit"] = None

        return self._build_signal(
            entry_signal=-1,
            price=price,
            time=time,
            volume=lot,
            reason="Pyramid Sell: price advanced by pyramid distance",
            comment="Pyrammid Sell",
            action="pyramid_sell",
            stop_loss=stop_loss,
            modify_existing_positions=True,
            clear_take_profit=True,
        )

    def _build_signal(
        self,
        entry_signal: int,
        price: float,
        time: Any,
        volume: float,
        reason: str,
        comment: str,
        action: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        modify_existing_positions: bool = False,
        clear_take_profit: bool = False,
    ) -> SignalDict:
        """
        Build the standardized signal dictionary expected by the template.

        Extra fields such as volume, action, comment, magic, and metadata are included
        so a richer HaruQuant execution engine can match the MT5 order comments and
        position-modification behavior.
        """
        return {
            "entry_signal": entry_signal,
            "exit_signal": 0,
            "pending_signal": 0,
            "cancel_pending_signal": 0,
            "price": float(self._normalize_price(price)),
            "time": time,
            "reason": reason,
            "stop_loss": None if stop_loss is None else float(self._normalize_price(stop_loss)),
            "take_profit": None if take_profit is None else float(self._normalize_price(take_profit)),
            "volume": float(self._normalize_lot(volume)),
            "lot_size": float(self._normalize_lot(volume)),
            "magic": self.ea_magic,
            "comment": comment,
            "action": action,
            "metadata": {
                "strategy": "White Fairy EA",
                "symbol": self.symbol,
                "timeframe": self.timeframe,
                "modify_existing_positions": modify_existing_positions,
                "clear_take_profit": clear_take_profit,
                "buy_count": self._num_buys(),
                "sell_count": self._num_sells(),
                "c_next_buy_price": self.c_next_buy_price,
                "c_next_sell_price": self.c_next_sell_price,
                "p_next_buy_price": self.p_next_buy_price,
                "p_next_sell_price": self.p_next_sell_price,
            },
        }
