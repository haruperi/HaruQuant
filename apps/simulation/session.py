"""
Simulation session manager.

Streams historical bars at variable speed and coordinates strategy/replay logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

import pandas as pd

from apps.indicator.momentum.rsi import rsi
from apps.indicator.trend.ema import ema
from apps.indicator.trend.sma import sma
from apps.utils.logger import logger
from apps.mt5.client import MT5Client
from apps.simulation.data import AccountInfoSimulator, SymbolInfoSimulator
from apps.simulation.simulator import TradeSimulator
from apps.sqlite import SQLiteDatabase


def _parse_time(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _serialize_time(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).isoformat()
    except ValueError:
        return str(value)


class SimulatorSession:
    """Stateful simulator session with streaming and persistence."""

    def __init__(self, session_id: int, config: dict[str, Any], db: SQLiteDatabase):
        """Initialize session state and simulator wiring."""
        self.session_id = session_id
        self.config = config
        self.db = db

        self.user_id = int(config.get("user_id", 0))
        self.symbol = config.get("symbol", "")
        self.timeframe = config.get("timeframe", "M1")
        self.mode = config.get("mode", "manual")
        self.speed_multiplier = float(config.get("speed_multiplier", 1.0) or 1.0)
        self.current_bar_index = int(config.get("current_bar_index", 0))
        self.total_bars = int(config.get("total_bars", 0))
        self.is_paused = config.get("status") == "paused"
        self.symbol_digits = int(config.get("symbol_digits", 5) or 5)

        self._bars: list[dict[str, Any]] = []
        self._data: Optional[pd.DataFrame] = None
        self._is_running = False

        self._mt5_client = MT5Client()
        self._mt5_connected = False
        self._mt5_creds = db.get_mt5_credentials(self.user_id) if self.user_id else None

        if self._mt5_creds:
            try:
                login = int(self._mt5_creds.get("login") or 0)
                password = self._mt5_creds.get("password") or ""
                server = self._mt5_creds.get("server") or ""
                path = self._mt5_creds.get("path") or ""
                if login and password and server:
                    self._mt5_connected = self._mt5_client.connect(
                        path=path,
                        login=login,
                        password=password,
                        server=server,
                    )
            except Exception as exc:
                logger.warning(f"Failed to connect MT5 client for session: {exc}")

        initial_balance = float(config.get("initial_balance") or 10000.0)
        account_info = AccountInfoSimulator(
            balance=initial_balance,
            equity=initial_balance,
            margin_free=initial_balance,
        )
        symbol_info = SymbolInfoSimulator.from_mt5_symbol(self.symbol)
        symbol_info.symbol = self.symbol
        self.symbol_digits = int(symbol_info.digits or self.symbol_digits)
        self.config["symbol_digits"] = self.symbol_digits

        self.simulator = TradeSimulator(
            simulator_name=config.get("session_name") or "SimulatorSession",
            mt5_client=self._mt5_client,
            account_info=account_info,
            symbols={self.symbol: symbol_info},
        )

        self._strategy = None
        self._replay_trades: list[dict[str, Any]] = []
        self._replay_index = 0

    def load_historical_bars(self) -> list[dict[str, Any]]:  # noqa: C901
        """Load bars based on config."""
        if self._bars:
            return self._bars

        bars_data = self.config.get("bars")
        if isinstance(bars_data, list) and bars_data:
            self._bars = list(bars_data)
            self._data = pd.DataFrame(self._bars)
            self.total_bars = len(self._bars)
            return self._bars

        start_time = _parse_time(self.config.get("start_time"))
        end_time = _parse_time(self.config.get("end_time"))
        number_of_bars = int(self.config.get("number_of_bars", 0) or 0)

        if not self._mt5_connected:
            creds = self._mt5_creds or {}
            login = int(creds.get("login") or 0)
            password = creds.get("password") or ""
            server = creds.get("server") or ""
            path = creds.get("path") or ""
            if not (login and password and server):
                raise RuntimeError("MT5 credentials not available for bar loading.")
            self._mt5_connected = self._mt5_client.connect(
                path=path,
                login=login,
                password=password,
                server=server,
            )
            if not self._mt5_connected:
                raise RuntimeError("Failed to initialize MT5 client for bars.")

        try:
            symbol_info = self._mt5_client.symbol_info(self.symbol)
            if symbol_info and symbol_info.digits is not None:
                self.symbol_digits = int(symbol_info.digits or self.symbol_digits)
                self.config["symbol_digits"] = self.symbol_digits

            if start_time and end_time:
                df = self._mt5_client.get_bars(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    date_from=start_time,
                    date_to=end_time,
                )
            else:
                count = number_of_bars if number_of_bars > 0 else 500
                df = self._mt5_client.get_bars(
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    count=count,
                )
        finally:
            pass

        if df is None or df.empty:
            raise ValueError("No historical bars loaded.")

        df = df.reset_index()
        df.rename(columns={"timestamp": "time"}, inplace=True)
        if "time" in df.columns:
            df["time"] = (
                pd.to_datetime(df["time"], errors="coerce")
                .dt.tz_localize(None)
                .dt.strftime("%Y-%m-%dT%H:%M:%S")
            )
        # Sort by time to ensure chronological order for chart rendering
        df = df.sort_values("time", ascending=True).reset_index(drop=True)
        logger.info(
            f"Loaded {len(df)} bars for {self.symbol} {self.timeframe} "
            f"from {df['time'].iloc[0] if len(df) else 'n/a'} "
            f"to {df['time'].iloc[-1] if len(df) else 'n/a'}"
        )
        self._data = df
        self._bars = df.to_dict(orient="records")
        self.total_bars = len(self._bars)
        return self._bars

    def get_bar(self, index: int) -> Optional[dict[str, Any]]:
        """Get a bar by index."""
        if not self._bars:
            self.load_historical_bars()
        if index < 0 or index >= len(self._bars):
            return None
        return self._bars[index]

    def process_bar_at_index(self, index: int) -> dict[str, Any]:
        """Process a bar and return account snapshot."""
        bar = self.get_bar(index)
        if not bar:
            return {}

        price = float(bar.get("close", bar.get("price", 0.0)) or 0.0)
        spread_points = float(bar.get("spread", 0.0) or 0.0)
        symbol_info = self.simulator._symbols_data.get(self.symbol)
        if symbol_info is not None:
            spread_points = float(spread_points or symbol_info.spread or 0.0)
            point = float(symbol_info.point or 0.00001)
        else:
            point = 0.00001

        bid = price
        ask = price + (spread_points * point)
        tick_time = (
            _parse_time(bar.get("time") or bar.get("timestamp")) or datetime.utcnow()
        )

        self.simulator._on_tick(
            symbol=self.symbol,
            tick_time=tick_time,
            bid=bid,
            ask=ask,
            last=price,
            log_every=0,
        )
        return {
            "balance": float(self.simulator._account_data.balance),
            "equity": float(self.simulator._account_data.equity),
            "margin": float(self.simulator._account_data.margin),
            "profit": float(self.simulator._account_data.profit),
            "margin_free": float(self.simulator._account_data.margin_free),
        }

    def get_indicators_at_index(self, index: int) -> dict[str, Any]:
        """Calculate indicators up to the given index."""
        if self._data is None or index < 1:
            return {}

        if not self.config.get("indicators_enabled", False):
            return {}

        window_sma = int(self.config.get("sma_period", 14))
        window_ema = int(self.config.get("ema_period", 14))
        window_rsi = int(self.config.get("rsi_period", 14))

        df = pd.DataFrame(self._bars[: index + 1])
        if "close" not in df.columns or df.empty:
            return {}

        payload: dict[str, Any] = {}

        try:
            if self.config.get("indicator_sma_enabled", False):
                payload["sma"] = (
                    sma(df, window=window_sma).iloc[-1].get(f"sma_{window_sma}")
                )
            if self.config.get("indicator_ema_enabled", False):
                payload["ema"] = (
                    ema(df, span=window_ema).iloc[-1].get(f"ema_{window_ema}")
                )
            if self.config.get("indicator_rsi_enabled", False):
                payload["rsi"] = (
                    rsi(df, period=window_rsi).iloc[-1].get(f"rsi_{window_rsi}")
                )
        except Exception:
            return {}

        if not payload:
            return {}

        payload["index"] = index
        payload["time"] = _serialize_time(df.iloc[-1].get("time"))
        return payload

    def set_strategy(self, strategy_instance: Any) -> None:
        """Attach a strategy instance for strategy mode."""
        self._strategy = strategy_instance
        try:
            strategy = self._strategy
            if strategy is None:
                return
            strategy.on_init()
        except Exception as exc:
            logger.warning(f"Strategy init failed: {exc}")

    def set_replay_trades(self, trades: list[dict[str, Any]]) -> None:
        """Attach replay trades for replay mode."""
        self._replay_trades = sorted(
            trades, key=lambda t: _parse_time(t.get("open_time")) or datetime.min
        )
        self._replay_index = 0

    def execute_trade(self, trade_request: dict[str, Any]) -> dict[str, Any] | None:
        """Execute a manual trade through the simulator."""
        side = str(trade_request.get("side", "")).lower()
        volume = float(trade_request.get("volume") or 0.0)
        sl = float(trade_request.get("sl") or 0.0)
        tp = float(trade_request.get("tp") or 0.0)

        # Get price from request or current bar
        price = float(trade_request.get("price") or 0.0)
        if price <= 0 and self.current_bar_index >= 0 and self._bars:
            bar_idx = min(self.current_bar_index, len(self._bars) - 1)
            current_bar = self._bars[bar_idx]
            price = float(current_bar.get("close", 0.0) or 0.0)

        if price <= 0:
            logger.warning(f"No valid price for trade execution: {price}")
            return None

        symbol_info = self.simulator._symbols_data.get(self.symbol)
        if symbol_info is not None:
            logger.info(
                f"Trade volume debug | symbol={self.symbol} volume={volume} "
                f"min={getattr(symbol_info, 'volume_min', None)} "
                f"step={getattr(symbol_info, 'volume_step', None)} "
                f"max={getattr(symbol_info, 'volume_max', None)} "
                f"request={trade_request!r}"
            )
        else:
            logger.info(
                f"Trade volume debug | symbol={self.symbol} volume={volume} "
                f"(no symbol_info) request={trade_request!r}"
            )

        now = datetime.utcnow()
        self.simulator._on_tick(
            symbol=self.symbol,
            tick_time=now,
            bid=price,
            ask=price,
            last=price,
            log_every=0,
        )

        if side == "buy":
            ok = self.simulator.open_position(
                action="buy",
                symbol=self.symbol,
                volume=volume,
                price=price,
                open_time=now,
                sl_price=sl,
                tp_price=tp,
                comment=trade_request.get("comment", ""),
            )
        elif side == "sell":
            ok = self.simulator.open_position(
                action="sell",
                symbol=self.symbol,
                volume=volume,
                price=price,
                open_time=now,
                sl_price=sl,
                tp_price=tp,
                comment=trade_request.get("comment", ""),
            )
        else:
            return None

        if not ok:
            logger.warning("Trade execution failed in simulator")
            return None

        position = None
        if self.simulator._positions_data:
            last_id = max(self.simulator._positions_data.keys())
            position = self.simulator._positions_data.get(last_id)
        if position is None:
            pos_data = {}
        else:
            pos_data = position._asdict() if hasattr(position, "_asdict") else {}

        payload = {
            "time": trade_request.get("time") or datetime.utcnow().isoformat(),
            "symbol": self.symbol,
            "side": side,
            "price": float(pos_data.get("price_open") or price),
            "volume": volume,
            "sl": float(pos_data.get("sl") or 0.0),
            "tp": float(pos_data.get("tp") or 0.0),
            "pnl": float(pos_data.get("profit") or 0.0),
            "reason": trade_request.get("reason", "manual"),
            "source": "manual",
        }
        self.db.save_trade(self.session_id, payload)
        return payload

    def place_pending_order(
        self, order_request: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Place a pending order through the simulator."""
        order_type = str(order_request.get("type", "")).lower()
        volume = float(order_request.get("volume") or 0.0)
        price = float(order_request.get("price") or 0.0)
        sl = float(order_request.get("sl") or 0.0)
        tp = float(order_request.get("tp") or 0.0)
        comment = order_request.get("comment") or ""
        expiry_date = order_request.get("expiry_date")
        expiration_mode = order_request.get("expiration_mode") or "gtc"

        if price <= 0:
            logger.warning("Pending order requires a valid price")
            return None

        # Ensure tick snapshot exists for validation logic
        current_price = price
        if self._bars and self.current_bar_index >= 0:
            bar_idx = min(self.current_bar_index, len(self._bars) - 1)
            current_bar = self._bars[bar_idx]
            current_price = float(
                current_bar.get("close", current_price) or current_price
            )

        now = datetime.utcnow()
        self.simulator._on_tick(
            symbol=self.symbol,
            tick_time=now,
            bid=current_price,
            ask=current_price,
            last=current_price,
            log_every=0,
        )

        if order_type == "buy_limit":
            ok = self.simulator.buy_limit(
                volume=volume,
                symbol=self.symbol,
                open_price=price,
                sl=sl,
                tp=tp,
                comment=comment,
                expiry_date=expiry_date,
                expiration_mode=expiration_mode,
            )
        elif order_type == "sell_limit":
            ok = self.simulator.sell_limit(
                volume=volume,
                symbol=self.symbol,
                open_price=price,
                sl=sl,
                tp=tp,
                comment=comment,
                expiry_date=expiry_date,
                expiration_mode=expiration_mode,
            )
        elif order_type == "buy_stop":
            ok = self.simulator.buy_stop(
                volume=volume,
                symbol=self.symbol,
                open_price=price,
                sl=sl,
                tp=tp,
                comment=comment,
                expiry_date=expiry_date,
                expiration_mode=expiration_mode,
            )
        elif order_type == "sell_stop":
            ok = self.simulator.sell_stop(
                volume=volume,
                symbol=self.symbol,
                open_price=price,
                sl=sl,
                tp=tp,
                comment=comment,
                expiry_date=expiry_date,
                expiration_mode=expiration_mode,
            )
        elif order_type == "buy_stop_limit":
            ok = self.simulator.buy_stop_limit(
                volume=volume,
                symbol=self.symbol,
                open_price=price,
                sl=sl,
                tp=tp,
                comment=comment,
                expiry_date=expiry_date,
                expiration_mode=expiration_mode,
            )
        elif order_type == "sell_stop_limit":
            ok = self.simulator.sell_stop_limit(
                volume=volume,
                symbol=self.symbol,
                open_price=price,
                sl=sl,
                tp=tp,
                comment=comment,
                expiry_date=expiry_date,
                expiration_mode=expiration_mode,
            )
        else:
            logger.warning(f"Unknown pending order type: {order_type}")
            return None

        if not ok:
            logger.warning("Pending order failed in simulator")
            return None

        payload = {
            "time": order_request.get("time") or datetime.utcnow().isoformat(),
            "symbol": self.symbol,
            "type": order_type,
            "price": price,
            "volume": volume,
            "sl": sl,
            "tp": tp,
            "comment": comment,
            "source": "manual",
        }
        return payload

    def pause(self) -> None:
        """Pause the simulation stream."""
        self.is_paused = True
        self.db.update_simulation_session(self.session_id, status="paused")

    def resume(self) -> None:
        """Resume the simulation stream."""
        self.is_paused = False
        self.db.update_simulation_session(self.session_id, status="running")

    def save_state(self) -> None:
        """Persist the current bar index to storage."""
        self.db.save_simulation_state(self.session_id, self.current_bar_index)

    def seek_to_bar(self, bar_index: int) -> None:
        """Jump the stream to a specific bar index."""
        self.current_bar_index = max(0, min(int(bar_index), len(self._bars) - 1))
        self.save_state()

    def stop(self) -> None:
        """Stop the simulation session."""
        self._is_running = False
        self.db.update_session_status(self.session_id, "completed")

