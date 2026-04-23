"""Data preparation pipeline for simulation backtests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

import pandas as pd

from backend.common.logger import logger
from backend.mcp.market_data_mcp import INTERVAL_TICK, OFFER_SIDE_BID, fetch
from backend.services.market_data.data_getters import load_dukascopy, load_parquet
from backend.services.market_data.data_manipulator import TicksGenerator
from backend.services.simulation.config import SimulationConfig, SimulationConfigError
from backend.services.simulation.strategy_registry import get_strategy_class


class SimulationDataPreparationError(RuntimeError):
    """Raised when simulation data preparation cannot produce ticks."""


@dataclass(frozen=True)
class PreparedSimulationData:
    """Prepared tick stream and metadata for a simulation run."""

    ticks: pd.DataFrame
    signal_bars_by_symbol: Mapping[str, pd.DataFrame] = field(default_factory=dict)
    tick_counts_by_symbol: Mapping[str, int] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)


class SimulationDataPreparer:
    """Prepare strategy signals and ticks for the simulation engine."""

    def __init__(self, engine: Any):
        self.engine = engine

    def prepare(self, config: SimulationConfig) -> PreparedSimulationData:
        """Prepare and merge all configured symbols into one tick stream."""
        merged_ticks: list[pd.DataFrame] = []
        signal_bars_by_symbol: dict[str, pd.DataFrame] = {}
        tick_counts_by_symbol: dict[str, int] = {}

        for symbol in config.data.symbols:
            prepared = self.prepare_symbol(config, symbol)
            merged_ticks.append(prepared.ticks)
            signal_bars_by_symbol[symbol] = prepared.signal_bars_by_symbol[symbol]
            tick_counts_by_symbol[symbol] = len(prepared.ticks)

        if not merged_ticks:
            raise SimulationDataPreparationError("no ticks generated for simulation")

        ticks = pd.concat(merged_ticks, axis=0).sort_index(kind="mergesort")
        metadata = {
            "symbols": tuple(config.data.symbols),
            "timeframe": config.data.timeframe,
            "tick_model": config.execution.tick_model,
            "spread_model": config.execution.spread_model,
            "start": config.data.start,
            "end": config.data.end,
            "warmup_start": config.data.warmup_start,
            "tick_count": int(len(ticks)),
            "tick_counts_by_symbol": dict(tick_counts_by_symbol),
        }
        return PreparedSimulationData(
            ticks=ticks,
            signal_bars_by_symbol=signal_bars_by_symbol,
            tick_counts_by_symbol=tick_counts_by_symbol,
            metadata=metadata,
        )

    def prepare_symbol(
        self,
        config: SimulationConfig,
        symbol: str,
    ) -> PreparedSimulationData:
        """Prepare signal bars and ticks for one symbol."""
        bars = self._load_bars(config, symbol, config.data.timeframe)
        if bars is None or bars.empty:
            raise SimulationDataPreparationError(f"no bars retrieved for {symbol}")

        signal_bars = self._run_strategy(config, symbol, bars)
        signal_bars = signal_bars[signal_bars.index >= config.data.start]
        if signal_bars is None or signal_bars.empty:
            raise SimulationDataPreparationError(
                f"no signal-ready bars available for {symbol} after start filter"
            )

        point_value = self._point_value(symbol)
        m1_data = self._load_m1_data_if_required(config, symbol)
        real_ticks = self._load_real_ticks_if_required(config, symbol)

        ticks_generator = TicksGenerator(
            model=config.execution.tick_model,
            trading_timeframe=config.data.timeframe,
            m1_data=m1_data,
            real_ticks=real_ticks,
            point_value=point_value,
            spread_model=config.execution.spread_model,
            fixed_spread_points=config.execution.spread_points,
            min_spread_points=config.execution.spread_min,
            max_spread_points=config.execution.spread_max,
        )
        ticks = ticks_generator.generate(signal_bars.copy())
        if ticks is None or ticks.empty:
            raise SimulationDataPreparationError(f"no ticks generated for {symbol}")

        ticks = ticks.copy()
        ticks["symbol"] = symbol
        ticks["signal_timeframe"] = config.data.timeframe

        logger.info(
            f"Prepared {len(ticks)} ticks for {symbol} using "
            f"{config.execution.tick_model}/{config.execution.spread_model}"
        )
        return PreparedSimulationData(
            ticks=ticks,
            signal_bars_by_symbol={symbol: signal_bars.copy()},
            tick_counts_by_symbol={symbol: len(ticks)},
            metadata={
                "symbol": symbol,
                "timeframe": config.data.timeframe,
                "tick_model": config.execution.tick_model,
                "spread_model": config.execution.spread_model,
                "point_value": point_value,
            },
        )

    def _run_strategy(
        self,
        config: SimulationConfig,
        symbol: str,
        bars: pd.DataFrame,
    ) -> pd.DataFrame:
        strategy_cls = get_strategy_class(config.strategy.name)
        params = dict(config.strategy.params)
        params["symbol"] = symbol
        strategy = strategy_cls(params=params)
        strategy.on_init()
        signal_bars = strategy.on_bar(bars.copy())
        if signal_bars is None or signal_bars.empty:
            raise SimulationDataPreparationError(
                f"strategy {config.strategy.name} produced no bars for {symbol}"
            )
        return signal_bars

    def _point_value(self, symbol: str) -> float:
        client = getattr(self.engine, "client", None)
        symbol_info_fn = getattr(client, "symbol_info", None)
        if symbol_info_fn is None:
            return 0.00001
        symbol_info = symbol_info_fn(symbol)
        return float(getattr(symbol_info, "point", 0.00001) or 0.00001)

    def _load_bars(
        self,
        config: SimulationConfig,
        symbol: str,
        timeframe: str,
    ) -> pd.DataFrame:
        if config.data.source == "metatrader":
            client = self._required_client()
            return client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                date_from=config.data.warmup_start,
                date_to=config.data.end,
            )
        if config.data.source == "dukascopy":
            return load_dukascopy(
                symbol=symbol,
                timeframe=timeframe,
                start_date=config.data.warmup_start.strftime("%Y-%m-%d"),
                end_date=config.data.end.strftime("%Y-%m-%d"),
            )
        if config.data.source == "local":
            return self._load_local_frame(config, symbol, "bars")
        raise SimulationConfigError(
            f"unsupported data.source for simulation preparation: {config.data.source}"
        )

    def _load_m1_data_if_required(
        self,
        config: SimulationConfig,
        symbol: str,
    ) -> Optional[pd.DataFrame]:
        if config.execution.tick_model not in {"m1_ticks", "synthetic_ticks"}:
            return None
        if config.data.source == "local":
            m1_data = self._load_local_frame(config, symbol, "m1")
        else:
            m1_data = self._load_bars(config, symbol, "M1")
        if m1_data is None or m1_data.empty:
            raise SimulationDataPreparationError(
                f"no M1 bars retrieved for {symbol}; "
                f"{config.execution.tick_model} requires M1 data"
            )
        return m1_data

    def _load_real_ticks_if_required(
        self,
        config: SimulationConfig,
        symbol: str,
    ) -> Optional[pd.DataFrame]:
        if config.execution.tick_model != "real_ticks":
            return None
        if config.data.source == "metatrader":
            client = self._required_client()
            ticks = client.get_ticks(
                symbol=symbol,
                start=config.data.warmup_start,
                end=config.data.end,
            )
        elif config.data.source == "local":
            ticks = self._load_local_frame(config, symbol, "ticks")
        elif config.data.source == "dukascopy":
            ticks = self._load_dukascopy_real_ticks(config, symbol)
        else:
            raise SimulationConfigError(
                f"unsupported data.source for real_ticks: {config.data.source}"
            )

        if ticks is None or ticks.empty:
            raise SimulationDataPreparationError(f"no real ticks retrieved for {symbol}")
        missing = {"bid", "ask"} - {str(col).lower() for col in ticks.columns}
        if missing:
            raise SimulationDataPreparationError(
                f"real tick data for {symbol} must contain bid and ask columns"
            )
        return ticks

    def _load_dukascopy_real_ticks(
        self,
        config: SimulationConfig,
        symbol: str,
    ) -> pd.DataFrame:
        dukas_symbol = f"{symbol[:3]}/{symbol[3:]}" if len(symbol) == 6 else symbol
        ticks = fetch(
            instrument=dukas_symbol,
            interval=INTERVAL_TICK,
            offer_side=OFFER_SIDE_BID,
            start=config.data.warmup_start,
            end=config.data.end,
        )
        if ticks is None or ticks.empty:
            return pd.DataFrame()

        out = ticks.copy()
        out.columns = [str(col).strip().lower() for col in out.columns]
        out = out.rename(
            columns={
                "bidprice": "bid",
                "askprice": "ask",
                "bidvolume": "bid_volume",
                "askvolume": "ask_volume",
            }
        )
        if "volume" not in out.columns and "bid_volume" in out.columns:
            out["volume"] = out["bid_volume"]
        if isinstance(out.index, pd.DatetimeIndex) and out.index.tz is not None:
            out.index = out.index.tz_convert("Europe/Athens").tz_localize(None)
        return self._slice_by_date(out.sort_index(), config.data.warmup_start, config.data.end)

    def _required_client(self) -> Any:
        client = getattr(self.engine, "client", None)
        if client is None:
            raise SimulationDataPreparationError("engine.client is required")
        return client

    def _load_local_frame(
        self,
        config: SimulationConfig,
        symbol: str,
        kind: str,
    ) -> pd.DataFrame:
        path = self._resolve_local_file(config, symbol, kind)
        frame = self._read_local_frame(path)
        frame = self._slice_by_date(frame, config.data.warmup_start, config.data.end)
        if frame.empty:
            raise SimulationDataPreparationError(
                f"local {kind} file for {symbol} has no rows in requested range: {path}"
            )
        return frame

    def _resolve_local_file(
        self,
        config: SimulationConfig,
        symbol: str,
        kind: str,
    ) -> Path:
        local_files = config.data.local_files
        aliases = {
            "bars": ("bars", "ohlcv", "data", "file", "path"),
            "m1": ("m1", "m1_bars", "minute_bars"),
            "ticks": ("ticks", "real_ticks", "tick_file"),
        }[kind]

        symbol_entry = self._lookup_mapping_key(local_files, symbol)
        if isinstance(symbol_entry, Mapping):
            path_value = self._first_mapping_value(symbol_entry, aliases)
        elif symbol_entry is not None and kind == "bars":
            path_value = symbol_entry
        else:
            path_value = self._first_mapping_value(local_files, aliases)

        if path_value is None:
            raise SimulationDataPreparationError(
                f"data.local_files must define {kind} file for {symbol}"
            )
        path = Path(str(path_value)).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists():
            raise SimulationDataPreparationError(f"local data file not found: {path}")
        return path

    @staticmethod
    def _lookup_mapping_key(mapping: Mapping[str, Any], key: str) -> Any:
        if key in mapping:
            return mapping[key]
        lower_key = key.lower()
        for candidate, value in mapping.items():
            if str(candidate).lower() == lower_key:
                return value
        return None

    @staticmethod
    def _first_mapping_value(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            if key in mapping:
                return mapping[key]
        lower = {str(key).lower(): value for key, value in mapping.items()}
        for key in keys:
            if key.lower() in lower:
                return lower[key.lower()]
        return None

    @staticmethod
    def _read_local_frame(path: Path) -> pd.DataFrame:
        suffix = path.suffix.lower()
        if suffix == ".csv":
            frame = pd.read_csv(path)
        elif suffix in {".parquet", ".pq"}:
            frame = load_parquet(path)
        else:
            raise SimulationDataPreparationError(
                f"unsupported local data file type for {path}; expected csv or parquet"
            )
        if frame is None or frame.empty:
            raise SimulationDataPreparationError(f"local data file is empty: {path}")
        return SimulationDataPreparer._normalize_local_frame(frame, path)

    @staticmethod
    def _normalize_local_frame(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
        data = frame.copy()
        data.columns = [str(col).strip().lower() for col in data.columns]

        if not isinstance(data.index, pd.DatetimeIndex):
            date_col = SimulationDataPreparer._detect_datetime_column(data)
            if date_col is None:
                raise SimulationDataPreparationError(
                    f"no datetime column detected in local data file: {path}"
                )
            data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
            data = data.dropna(subset=[date_col]).set_index(date_col)
        else:
            data.index = pd.to_datetime(data.index, errors="coerce")
            data = data[~data.index.isna()]

        rename_map = {
            "tick_volume": "volume",
            "tickvolume": "volume",
            "vol": "volume",
            "datetime": "timestamp",
            "date": "timestamp",
            "time": "timestamp",
        }
        data = data.rename(columns={k: v for k, v in rename_map.items() if k in data.columns})
        numeric_columns = {
            "open",
            "high",
            "low",
            "close",
            "volume",
            "spread",
            "bid",
            "ask",
            "last",
        }
        for col in numeric_columns & set(data.columns):
            data[col] = pd.to_numeric(data[col], errors="coerce")

        data.index = pd.DatetimeIndex(data.index, name="Datetime")
        return data.sort_index()

    @staticmethod
    def _detect_datetime_column(frame: pd.DataFrame) -> Optional[str]:
        hints = ("timestamp", "datetime", "date", "time", "ts")
        for hint in hints:
            if hint in frame.columns:
                return hint
        for col in frame.columns:
            lowered = str(col).lower()
            if any(hint in lowered for hint in hints):
                return str(col)
        return None

    @staticmethod
    def _slice_by_date(
        frame: pd.DataFrame,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        index = pd.DatetimeIndex(frame.index)
        mask = (index >= pd.Timestamp(start)) & (index <= pd.Timestamp(end))
        return frame.loc[mask].copy()
