"""
MT5-like strategy tester (Part 04).

Runs a TradeSimulator over historical ticks/bars using a simple config dict.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from heapq import heappop, heappush
from typing import Any, Callable, Iterable, Optional

import MetaTrader5 as mt5
from tqdm import tqdm

from apps.logger import logger
from apps.simulator.engine import TradeSimulator
from apps.simulator.gateway import TradeGateway
from apps.simulator.market_data import MarketDataStore
from apps.simulator.ticks_gen import TicksGen

TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1,
    "M2": mt5.TIMEFRAME_M2,
    "M3": mt5.TIMEFRAME_M3,
    "M4": mt5.TIMEFRAME_M4,
    "M5": mt5.TIMEFRAME_M5,
    "M6": mt5.TIMEFRAME_M6,
    "M10": mt5.TIMEFRAME_M10,
    "M12": mt5.TIMEFRAME_M12,
    "M15": mt5.TIMEFRAME_M15,
    "M20": mt5.TIMEFRAME_M20,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H2": mt5.TIMEFRAME_H2,
    "H3": mt5.TIMEFRAME_H3,
    "H4": mt5.TIMEFRAME_H4,
    "H6": mt5.TIMEFRAME_H6,
    "H8": mt5.TIMEFRAME_H8,
    "H12": mt5.TIMEFRAME_H12,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


@dataclass(frozen=True)
class TesterConfig:
    """Normalized tester configuration values."""

    bot_name: str
    symbols: list[str]
    timeframe: int
    start_date: datetime
    end_date: datetime
    modelling: str
    deposit: float
    leverage: str


class TesterConfigValidators:
    """Validate and parse tester configurations."""

    REQUIRED_KEYS = {
        "bot_name",
        "symbols",
        "timeframe",
        "start_date",
        "end_date",
        "modelling",
        "deposit",
        "leverage",
    }

    VALID_MODELLING = {
        "real_ticks",
        "every_tick",
        "simulated_ticks",
        "new_bar",
        "1-minute-ohlc",
        "1_minute_ohlc",
        "1m_ohlc",
    }

    @staticmethod
    def parse(raw_config: dict[str, Any]) -> TesterConfig:
        """Parse and validate raw tester configuration input."""
        TesterConfigValidators._validate_keys(raw_config)

        bot_name = str(raw_config["bot_name"])
        symbols = raw_config["symbols"]
        if not isinstance(symbols, list) or not symbols:
            raise RuntimeError("symbols must be a non-empty list")

        timeframe_text = str(raw_config["timeframe"]).upper()
        if timeframe_text not in TIMEFRAMES:
            raise RuntimeError(f"Invalid timeframe: {timeframe_text}")
        timeframe = TIMEFRAMES[timeframe_text]

        modelling = str(raw_config["modelling"]).lower()
        if modelling not in TesterConfigValidators.VALID_MODELLING:
            raise RuntimeError(f"Invalid modelling mode: {modelling}")

        start_date = TesterConfigValidators._parse_date(raw_config["start_date"])
        end_date = TesterConfigValidators._parse_date(raw_config["end_date"])
        if start_date >= end_date:
            raise RuntimeError("start_date must be earlier than end_date")

        deposit = float(raw_config["deposit"])
        if deposit <= 0:
            raise RuntimeError("deposit must be > 0")

        leverage = str(raw_config["leverage"])

        return TesterConfig(
            bot_name=bot_name,
            symbols=[str(symbol) for symbol in symbols],
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            modelling=modelling,
            deposit=deposit,
            leverage=leverage,
        )

    @staticmethod
    def _validate_keys(raw_config: dict[str, Any]) -> None:
        """Validate required config keys."""
        provided_keys = set(raw_config.keys())
        missing = TesterConfigValidators.REQUIRED_KEYS - provided_keys
        if missing:
            raise RuntimeError(f"Missing tester config keys: {missing}")
        extra = provided_keys - TesterConfigValidators.REQUIRED_KEYS
        if extra:
            raise RuntimeError(f"Unknown tester config keys: {extra}")

    @staticmethod
    def _parse_date(value: Any) -> datetime:
        """Parse dates in DD.MM.YYYY HH:MM format to UTC."""
        if isinstance(value, datetime):
            return value.replace(tzinfo=timezone.utc)
        try:
            parsed = datetime.strptime(str(value), "%d.%m.%Y %H:%M")
        except ValueError as exc:
            raise RuntimeError("Date format must be: DD.MM.YYYY HH:MM") from exc
        return parsed.replace(tzinfo=timezone.utc)


class Tester:
    """Strategy tester runner using TradeSimulator and MarketDataStore."""

    def __init__(
        self,
        tester_config: dict[str, Any],
        mt5_instance: Optional[Any] = None,
        data_store: Optional[MarketDataStore] = None,
    ) -> None:
        """Initialize the tester with configuration and data access."""
        self.config = TesterConfigValidators.parse(tester_config)
        self.mt5_instance = mt5_instance
        self.data_store = data_store or MarketDataStore()
        self.sim = TradeSimulator(
            simulator_name=self.config.bot_name,
            deposit=self.config.deposit,
            leverage=self.config.leverage,
        )
        self.gateway = TradeGateway(self.sim)
        self.trade = self.gateway.get_trade(is_tester=True)
        self.TESTER_ALL_TICKS_INFO: list[dict[str, Any]] = []
        self.TESTER_ALL_BARS_INFO: list[dict[str, Any]] = []

    def OnTick(
        self, on_tick: Optional[Callable[[], None]] = None, **kwargs: Any
    ) -> None:
        """Register and run the tester loop with an MT5-like OnTick callback."""
        if on_tick is None:
            on_tick = kwargs.get("ontick_func")
        if on_tick is None:
            raise RuntimeError("OnTick requires a callback function.")
        self._ensure_data()
        self._prepare_streams()
        self._tester_init()
        self.run(lambda _sim, _tick: on_tick())
        self._tester_deinit()

    def run(
        self,
        on_tick: Callable[[TradeSimulator, Any], None],
    ) -> None:
        """Run the tester loop for the configured modelling mode."""
        modelling = self.config.modelling
        if modelling in ("real_ticks", "every_tick"):
            self._run_tick_mode(on_tick)
        elif modelling in ("new_bar", "1-minute-ohlc", "1_minute_ohlc", "1m_ohlc"):
            self._run_bar_mode(on_tick)
        else:
            self._run_simulated_mode(on_tick)

    def _run_tick_mode(self, on_tick: Callable[[TradeSimulator, Any], None]) -> None:
        total_ticks = sum(info["size"] for info in self.TESTER_ALL_TICKS_INFO)
        logger.debug(
            f"{self.config.bot_name}.tester | [tester.py:OnTick] => "
            f"total number of ticks: {total_ticks}"
        )
        self._stats = {"ticks": total_ticks, "bars": 0}
        with tqdm(total=total_ticks, desc="Tester Progress", unit="tick") as pbar:
            while True:
                self._monitor_all()
                any_tick_processed = False

                for ticks_info in self.TESTER_ALL_TICKS_INFO:
                    symbol = ticks_info["symbol"]
                    size = ticks_info["size"]
                    counter = ticks_info["counter"]

                    if counter >= size:
                        continue

                    current_tick = ticks_info["ticks"][counter]
                    self._step(symbol, current_tick, on_tick)
                    ticks_info["counter"] = counter + 1
                    any_tick_processed = True
                    pbar.update(1)

                if not any_tick_processed:
                    break

    def _run_bar_mode(self, on_tick: Callable[[TradeSimulator, Any], None]) -> None:
        total_bars = sum(info["size"] for info in self.TESTER_ALL_BARS_INFO)
        logger.debug(
            f"{self.config.bot_name}.tester | [tester.py:OnTick] => "
            f"total number of bars: {total_bars}"
        )
        self._stats = {"ticks": 0, "bars": total_bars}
        with tqdm(total=total_bars, desc="Tester Progress", unit="bar") as pbar:
            while True:
                self._monitor_all()
                any_bar_processed = False

                for bars_info in self.TESTER_ALL_BARS_INFO:
                    symbol = bars_info["symbol"]
                    size = bars_info["size"]
                    counter = bars_info["counter"]

                    if counter >= size:
                        continue

                    bar = bars_info["bars"][counter]
                    current_tick = self._bar_to_tick(symbol, bar)
                    self._step(symbol, current_tick, on_tick)
                    bars_info["counter"] = counter + 1
                    any_bar_processed = True
                    pbar.update(1)

                if not any_bar_processed:
                    break

    def _run_simulated_mode(
        self, on_tick: Callable[[TradeSimulator, Any], None]
    ) -> None:
        for symbol, tick in self._iter_simulated_ticks():
            self._step(symbol, tick, on_tick)

    def _step(
        self,
        symbol: str,
        tick: dict[str, Any],
        on_tick: Callable[[TradeSimulator, Any], None],
    ) -> None:
        self.sim.update_tick(symbol, tick)
        on_tick(self.sim, tick)

    def _monitor_all(self) -> None:
        self.sim.monitor_pending_orders()
        self.sim.monitor_positions(verbose=False)
        self.sim.monitor_account(verbose=False)

    def _ensure_data(self) -> None:
        if self.mt5_instance is None and not mt5.initialize():
            return
        for symbol in self.config.symbols:
            if self.config.modelling in ("real_ticks", "every_tick"):
                self._fetch_historical_ticks(symbol)
            else:
                bars = self.data_store.read_bars_range(
                    symbol,
                    self.config.timeframe,
                    self.config.start_date,
                    self.config.end_date,
                )
                if not bars:
                    self.data_store.fetch_bars_range(
                        symbol,
                        self.config.timeframe,
                        self.config.start_date,
                        self.config.end_date,
                    )

    def _prepare_streams(self) -> None:
        self.TESTER_ALL_TICKS_INFO.clear()
        self.TESTER_ALL_BARS_INFO.clear()

        modelling = self.config.modelling
        for symbol in self.config.symbols:
            if modelling == "real_ticks":
                ticks = self.data_store.read_ticks_range(
                    symbol, self.config.start_date, self.config.end_date
                )
                if ticks:
                    self.TESTER_ALL_TICKS_INFO.append(
                        {
                            "symbol": symbol,
                            "ticks": ticks,
                            "size": len(ticks),
                            "counter": 0,
                        }
                    )
            elif modelling == "every_tick":
                bars = self.data_store.read_bars_range(
                    symbol,
                    mt5.TIMEFRAME_M1,
                    self.config.start_date,
                    self.config.end_date,
                )
                ticks = TicksGen.generate_ticks_from_bars(
                    bars=bars,
                    symbol=symbol,
                    symbol_point=self._symbol_point(symbol),
                )
                if ticks:
                    self.TESTER_ALL_TICKS_INFO.append(
                        {
                            "symbol": symbol,
                            "ticks": ticks,
                            "size": len(ticks),
                            "counter": 0,
                        }
                    )
            elif modelling in ("new_bar", "1-minute-ohlc", "1_minute_ohlc", "1m_ohlc"):
                timeframe = (
                    mt5.TIMEFRAME_M1
                    if modelling != "new_bar"
                    else self.config.timeframe
                )
                bars = self.data_store.read_bars_range(
                    symbol, timeframe, self.config.start_date, self.config.end_date
                )
                if bars:
                    self.TESTER_ALL_BARS_INFO.append(
                        {
                            "symbol": symbol,
                            "bars": bars,
                            "size": len(bars),
                            "counter": 0,
                        }
                    )

    def _iter_real_ticks(
        self, streams: list[tuple[str, list[dict[str, Any]]]]
    ) -> Iterable[tuple[str, dict[str, Any]]]:

        heap: list[tuple[int, int, str]] = []
        indexes = {}
        for idx, (symbol, ticks) in enumerate(streams):
            if ticks:
                time_value = int(ticks[0].get("time", 0))
                heappush(heap, (time_value, idx, symbol))
                indexes[symbol] = 0

        while heap:
            _, stream_idx, symbol = heappop(heap)
            ticks = streams[stream_idx][1]
            tick_idx = indexes[symbol]
            tick = ticks[tick_idx]
            yield symbol, tick
            tick_idx += 1
            indexes[symbol] = tick_idx
            if tick_idx < len(ticks):
                time_value = int(ticks[tick_idx].get("time", 0))
                heappush(heap, (time_value, stream_idx, symbol))

    def _iter_simulated_ticks(self) -> Iterable[tuple[str, dict[str, Any]]]:
        for symbol, bar in self._iter_bars(timeframe=mt5.TIMEFRAME_M1):
            for tick in self._bar_to_sim_ticks(bar, symbol):
                yield symbol, tick

    def _iter_ohlc_ticks(self) -> Iterable[tuple[str, dict[str, Any]]]:
        for symbol, bar in self._iter_bars(timeframe=mt5.TIMEFRAME_M1):
            for tick in self._bar_to_ohlc_ticks(bar, symbol):
                yield symbol, tick

    def _fetch_historical_ticks(self, symbol: str) -> None:
        for month_start in self._month_starts(
            self.config.start_date, self.config.end_date
        ):
            month_end = self._month_end(month_start, self.config.end_date)
            logger.info(
                f"{self.config.bot_name}.tester | [ticks.py:67 - fetch_historical_ticks] "
                f"Processing ticks for {symbol}: "
                f"{month_start.strftime('%Y-%m-%d')} -> {month_end.strftime('%Y-%m-%d')}"
            )
            ticks = self.data_store.read_ticks_range(symbol, month_start, month_end)
            if not ticks:
                ticks = self.data_store.fetch_ticks_range(
                    symbol, month_start, month_end, mt5.COPY_TICKS_ALL
                )
            if not ticks:
                logger.warning(
                    f"{self.config.bot_name}.tester | [ticks.py:67 - fetch_historical_ticks] "
                    f"No ticks for {symbol} {month_start.strftime('%Y-%m')}"
                )

    def _month_starts(self, start: datetime, end: datetime) -> list[datetime]:
        current = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        results = []
        while current <= end:
            results.append(current)
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        return results

    def _month_end(self, month_start: datetime, end: datetime) -> datetime:
        if month_start.month == 12:
            next_month = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month = month_start.replace(month=month_start.month + 1)
        month_end = next_month - timedelta(seconds=1)
        return month_end if month_end < end else end

    def _iter_bars(
        self, timeframe: Optional[int] = None
    ) -> Iterable[tuple[str, dict[str, Any]]]:
        tf = timeframe if timeframe is not None else self.config.timeframe
        for symbol in self.config.symbols:
            bars = self.data_store.read_bars_range(
                symbol, tf, self.config.start_date, self.config.end_date
            )
            for bar in bars:
                yield symbol, bar

    def _bar_to_tick(self, symbol: str, bar: dict[str, Any]) -> dict[str, Any]:
        price = float(bar.get("open", bar.get("close", 0.0)))
        spread = float(bar.get("spread", 0.0))
        point = self._symbol_point(symbol)
        return {
            "symbol": symbol,
            "time": int(bar.get("time", 0)),
            "bid": price,
            "ask": price + spread * point,
            "last": price,
            "volume": int(bar.get("tick_volume", 0)),
            "time_msc": int(bar.get("time", 0)) * 1000,
            "flags": 0,
            "volume_real": float(bar.get("real_volume", 0.0)),
        }

    def _bar_to_sim_ticks(
        self, bar: dict[str, Any], symbol: str
    ) -> list[dict[str, Any]]:
        open_price = float(bar.get("open", 0.0))
        high_price = float(bar.get("high", open_price))
        low_price = float(bar.get("low", open_price))
        close_price = float(bar.get("close", open_price))
        base_time = int(bar.get("time", 0))
        sequence = [open_price, high_price, low_price, close_price]
        ticks = []
        for idx, price in enumerate(sequence):
            ticks.append(
                {
                    "symbol": symbol,
                    "time": base_time + idx * 10,
                    "bid": price,
                    "ask": price,
                    "last": price,
                    "volume": int(bar.get("tick_volume", 0)),
                    "time_msc": (base_time + idx * 10) * 1000,
                    "flags": 0,
                    "volume_real": float(bar.get("real_volume", 0.0)),
                }
            )
        return ticks

    def _bar_to_ohlc_ticks(
        self, bar: dict[str, Any], symbol: str
    ) -> list[dict[str, Any]]:
        return self._bar_to_sim_ticks(bar, symbol)

    def _symbol_point(self, symbol: str) -> float:
        info = self.sim.symbol_info(symbol) or {}
        return float(info.get("point", 0.00001))

    def _tester_init(self) -> None:
        self._stats = {"ticks": 0, "bars": 0}
        balance_deal = {
            "id": self._generate_ticket(),
            "time": self.config.start_date,
            "symbol": "",
            "type": "balance",
            "entry": "in",
            "volume": 0.0,
            "price": 0.0,
            "commission": 0.0,
            "swap": 0.0,
            "profit": 0.0,
            "comment": "",
            "balance": self.sim.account_info().balance,
        }
        self.sim.deals_container.append(balance_deal)

    def _tester_deinit(self) -> None:
        output_file = f"Reports/{self.config.bot_name}-report.html"
        self._generate_tester_report(output_file=output_file)
        print(f"Deals report saved to: {output_file}")

    def _generate_tester_report(self, output_file: str) -> None:
        template_path = "Reports/template.html"
        with open(template_path, "r", encoding="utf-8") as file:
            template = file.read()

        order_rows_html = self._render_order_rows(self.sim.orders_history_container)
        deal_rows_html = self._render_deal_rows(self.sim.deals_container)
        stat_rows_html = self._render_stats_rows()

        html = (
            template.replace("{{ORDER_ROWS}}", order_rows_html)
            .replace("{{DEAL_ROWS}}", deal_rows_html)
            .replace("{{STAT_ROWS}}", stat_rows_html)
        )

        with open(output_file, "w", encoding="utf-8") as file:
            file.write(html)

    def _render_order_rows(self, orders: list[dict[str, Any]]) -> str:
        rows = []
        for order in orders:
            open_time = self._format_time(order.get("time"))
            rows.append(
                "\n".join(
                    [
                        "<tr>",
                        f"<td>{open_time}</td>",
                        f"<td>{order.get('id', '')}</td>",
                        f"<td>{order.get('symbol', '')}</td>",
                        f"<td>{order.get('type', '')}</td>",
                        f"<td class=\"text-end\">{order.get('volume', 0):.2f}</td>",
                        f"<td class=\"text-end\">{order.get('open_price', 0):.5f}</td>",
                        f"<td class=\"text-end\">{self._format_price(order.get('sl'))}</td>",
                        f"<td class=\"text-end\">{self._format_price(order.get('tp'))}</td>",
                        "<td></td>",
                        "<td>Placed</td>",
                        f"<td>{order.get('comment', '')}</td>",
                        "</tr>",
                    ]
                )
            )
        return "\n".join(rows)

    def _render_deal_rows(self, deals: list[dict[str, Any]]) -> str:
        rows = []
        for deal in deals:
            rows.append(
                "\n".join(
                    [
                        "<tr>",
                        f"<td>{self._format_time(deal.get('time'))}</td>",
                        f"<td>{deal.get('id', '')}</td>",
                        f"<td>{deal.get('symbol', '')}</td>",
                        f"<td>{deal.get('type', '')}</td>",
                        f"<td>{deal.get('entry', '')}</td>",
                        f"<td class=\"text-end\">{deal.get('volume', 0):.2f}</td>",
                        f"<td class=\"text-end\">{deal.get('price', 0):.5f}</td>",
                        f"<td class=\"text-end\">{deal.get('commission', 0):.2f}</td>",
                        f"<td class=\"text-end\">{deal.get('swap', 0):.2f}</td>",
                        f"<td class=\"text-end\">{deal.get('profit', 0):.2f}</td>",
                        f"<td>{deal.get('comment', '')}</td>",
                        f"<td>{deal.get('balance', '')}</td>",
                        "</tr>",
                    ]
                )
            )
        return "\n".join(rows)

    def _render_stats_rows(self) -> str:
        net_profit = sum(d.get("profit", 0.0) for d in self.sim.deals_container)
        gross_profit = sum(
            d.get("profit", 0.0)
            for d in self.sim.deals_container
            if d.get("profit", 0.0) > 0
        )
        gross_loss = sum(
            d.get("profit", 0.0)
            for d in self.sim.deals_container
            if d.get("profit", 0.0) < 0
        )
        total_trades = sum(
            1 for d in self.sim.deals_container if d.get("type") not in ("balance", "")
        )
        profit_factor = (gross_profit / abs(gross_loss)) if gross_loss else 0.0
        expected_payoff = (net_profit / total_trades) if total_trades else 0.0
        symbols = len(self.config.symbols)
        ticks = self._stats.get("ticks", 0)
        bars = self._stats.get("bars", 0)
        history_quality = 100.0 if ticks or bars else 0.0

        stats = {
            "History Quality": f"{history_quality:.2f}%",
            "Bars": bars,
            "Ticks": ticks,
            "Symbols": symbols,
            "Total Net Profit": f"{net_profit:.2f}",
            "Gross Profit": f"{gross_profit:.2f}",
            "Gross Loss": f"{gross_loss:.2f}",
            "Profit Factor": f"{profit_factor:.2f}",
            "Expected Payoff": f"{expected_payoff:.2f}",
            "Total Trades": total_trades,
        }
        rows = []
        for key, value in stats.items():
            rows.append(f"<tr><td>{key}</td><td>{value}</td></tr>")
        return "\n".join(rows)

    def _format_time(self, value: Any) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(int(value), tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        return ""

    def _format_price(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (int, float)) and float(value) == 0:
            return ""
        try:
            return f"{float(value):.5f}"
        except (TypeError, ValueError):
            return ""

    def _generate_ticket(self) -> int:
        return int(datetime.now(tz=timezone.utc).timestamp() * 1000)
