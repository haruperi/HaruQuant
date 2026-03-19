"""Canonical portfolio-state builder for the risk subsystem."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

from apps.risk.models import (
    AccountState,
    MarketState,
    PortfolioState,
    PositionState,
    SymbolState,
)
from apps.risk.limits import RiskLimits
from apps.risk.validators import (
    ValidationSummary,
    validate_account_state,
    validate_market_states,
    validate_position_states,
    validate_risk_limits,
    validate_symbol_states,
)


class PortfolioStateEngine:
    """Normalize existing raw risk inputs into one validated portfolio state."""

    def build_state_from_engine(
        self,
        engine: Any,
        symbols: List[str],
        timeframe: str = "D1",
        count: int = 500,
        start_pos: int = 0,
        as_of: Optional[str] = None,
        bar_index: Optional[int] = None,
        positions: Any = None,
        account: Any = None,
        limits: Optional[RiskLimits] = None,
        symbol_to_cluster: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PortfolioState:
        """Build a validated portfolio state directly from the existing engine stack.

        This is a thin Phase 1.5 helper for deterministic point-in-time reconstruction:
        - account defaults to the current engine account snapshot
        - positions defaults to the current engine position snapshot
        - symbol specs default to `engine.symbol_info(symbol)`
        - market data defaults to bars fetched from `engine.client.get_bars(...)`
        - bars can be trimmed either by `as_of` timestamp or by `bar_index`
        """
        resolved_account = account if account is not None else self._engine_account(engine)
        resolved_positions = (
            positions if positions is not None else self._engine_positions(engine)
        )
        symbol_specs = self._engine_symbol_specs(engine, symbols)
        market_data = self._engine_market_data(
            engine=engine,
            symbols=symbols,
            timeframe=timeframe,
            count=count,
            start_pos=start_pos,
            as_of=as_of,
            bar_index=bar_index,
        )

        resolved_as_of = as_of
        if resolved_as_of is None and market_data:
            latest_timestamps = [
                df.index[-1] for df in market_data.values() if isinstance(df.index, pd.DatetimeIndex) and not df.empty
            ]
            if latest_timestamps:
                resolved_as_of = pd.Timestamp(max(latest_timestamps)).isoformat()

        merged_metadata = {
            "source": "engine_snapshot",
            "timeframe": timeframe,
            "count": count,
            "start_pos": start_pos,
            **dict(metadata or {}),
        }
        if bar_index is not None:
            merged_metadata["bar_index"] = int(bar_index)
        if as_of is not None:
            merged_metadata["requested_as_of"] = str(as_of)

        return self.build_state(
            account=resolved_account,
            positions=resolved_positions,
            symbol_specs=symbol_specs,
            market_data=market_data,
            limits=limits,
            symbol_to_cluster=symbol_to_cluster,
            timeframe=timeframe,
            as_of=resolved_as_of,
            metadata=merged_metadata,
        )

    def build_state(
        self,
        account: Any,
        positions: Any,
        symbol_specs: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, pd.DataFrame]] = None,
        limits: Optional[RiskLimits] = None,
        symbol_to_cluster: Optional[Dict[str, str]] = None,
        timeframe: str = "D1",
        as_of: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PortfolioState:
        """Build a validated canonical portfolio state."""
        account_state = self._normalize_account(account)
        position_states = self._normalize_positions(positions, symbol_to_cluster or {})
        symbol_states = self._normalize_symbol_specs(symbol_specs or {}, position_states)
        market_states = self._normalize_market_data(market_data or {}, timeframe)

        summary = ValidationSummary()
        summary = summary.extend(validate_account_state(account_state))
        summary = summary.extend(validate_position_states(position_states))
        summary = summary.extend(validate_symbol_states(symbol_states, position_states))
        summary = summary.extend(validate_market_states(market_states, position_states))
        if limits is not None:
            summary = summary.extend(validate_risk_limits(limits))

        exposures = self._compute_exposures(position_states, symbol_states, market_states)
        return PortfolioState(
            account=account_state,
            positions=position_states,
            symbols=symbol_states,
            markets=market_states,
            limits=limits,
            symbol_to_cluster=dict(symbol_to_cluster or {}),
            validation_summary=summary,
            exposures=exposures,
            as_of=as_of,
            metadata=dict(metadata or {}),
        )

    def _normalize_account(self, account: Any) -> AccountState:
        if isinstance(account, AccountState):
            return account

        payload = self._to_dict(account)
        equity = self._get_first(payload, "equity")
        if equity is None:
            balance = self._get_first(payload, "balance")
            equity = balance if balance is not None else 0.0

        return AccountState(
            equity=float(equity),
            balance=self._to_float(self._get_first(payload, "balance")),
            free_margin=self._to_float(
                self._get_first(payload, "free_margin", "margin_free")
            ),
            margin_used=self._to_float(
                self._get_first(payload, "margin_used", "margin")
            ),
            currency=self._to_str(self._get_first(payload, "currency", "currency_code")),
            account_id=self._to_str(self._get_first(payload, "account_id", "login", "id")),
            metadata=self._strip_known_keys(
                payload,
                {
                    "equity",
                    "balance",
                    "free_margin",
                    "margin_free",
                    "margin_used",
                    "margin",
                    "currency",
                    "currency_code",
                    "account_id",
                    "login",
                    "id",
                },
            ),
        )

    def _engine_account(self, engine: Any) -> Any:
        if hasattr(engine, "account_info"):
            return engine.account_info()
        if hasattr(engine, "api") and hasattr(engine.api, "account_info"):
            return engine.api.account_info()
        return {}

    def _engine_positions(self, engine: Any) -> Any:
        if hasattr(engine, "positions_get"):
            return engine.positions_get()
        if hasattr(engine, "api") and hasattr(engine.api, "positions_get"):
            return engine.api.positions_get()
        return []

    def _engine_symbol_specs(self, engine: Any, symbols: List[str]) -> Dict[str, Any]:
        symbol_specs: Dict[str, Any] = {}
        for symbol in symbols:
            spec = None
            if hasattr(engine, "symbol_info"):
                spec = engine.symbol_info(symbol)
            elif hasattr(engine, "api") and hasattr(engine.api, "symbol_info"):
                spec = engine.api.symbol_info(symbol)
            if spec is not None:
                symbol_specs[symbol] = spec
        return symbol_specs

    def _engine_market_data(
        self,
        engine: Any,
        symbols: List[str],
        timeframe: str,
        count: int,
        start_pos: int,
        as_of: Optional[str],
        bar_index: Optional[int],
    ) -> Dict[str, pd.DataFrame]:
        client = getattr(engine, "client", None)
        if client is None or not hasattr(client, "get_bars"):
            return {}

        market_data: Dict[str, pd.DataFrame] = {}
        resolved_as_of = pd.Timestamp(as_of) if as_of is not None else None

        for symbol in symbols:
            bars = client.get_bars(
                symbol=symbol,
                timeframe=timeframe,
                count=count,
                start_pos=start_pos,
            )
            if bars is None or bars.empty:
                continue

            prepared = bars.copy()
            if resolved_as_of is not None and isinstance(prepared.index, pd.DatetimeIndex):
                prepared = prepared[prepared.index <= resolved_as_of]

            if bar_index is not None and not prepared.empty:
                idx = int(bar_index)
                if idx >= 0:
                    prepared = prepared.iloc[: idx + 1]
                else:
                    prepared = prepared.iloc[: len(prepared) + idx + 1]

            market_data[symbol] = prepared.copy()

        return market_data

    def _normalize_positions(
        self,
        positions: Any,
        symbol_to_cluster: Dict[str, str],
    ) -> List[PositionState]:
        if positions is None:
            return []

        out: List[PositionState] = []
        if isinstance(positions, dict):
            if positions and all(isinstance(key, str) for key in positions.keys()):
                for symbol, value in positions.items():
                    if isinstance(value, PositionState):
                        out.append(value)
                        continue
                    if isinstance(value, (int, float)):
                        out.append(
                            PositionState(
                                symbol=symbol,
                                lots=float(value),
                                side="LONG" if float(value) >= 0 else "SHORT",
                                cluster=symbol_to_cluster.get(symbol),
                            )
                        )
                        continue

                    payload = self._to_dict(value)
                    payload["symbol"] = symbol
                    out.append(self._build_position_state(payload, symbol_to_cluster))
                return [position for position in out if position.lots != 0]

        iterable: Iterable[Any] = positions if isinstance(positions, Iterable) else [positions]
        for item in iterable:
            if isinstance(item, PositionState):
                out.append(item)
            else:
                out.append(
                    self._build_position_state(self._to_dict(item), symbol_to_cluster)
                )
        return [position for position in out if position.lots != 0]

    def _build_position_state(
        self,
        payload: Dict[str, Any],
        symbol_to_cluster: Dict[str, str],
    ) -> PositionState:
        symbol = str(self._get_first(payload, "symbol", "Symbol") or "")
        lots_raw = self._get_first(payload, "lots", "volume", "Volume")
        lots = float(lots_raw or 0.0)
        side = self._normalize_side(self._get_first(payload, "side", "type"), lots)
        signed_lots = abs(lots) if side == "LONG" else -abs(lots)
        return PositionState(
            symbol=symbol,
            lots=signed_lots,
            side=side,
            entry_price=self._to_float(self._get_first(payload, "entry_price", "price_open")),
            stop_loss=self._to_float(self._get_first(payload, "stop_loss", "sl")),
            take_profit=self._to_float(self._get_first(payload, "take_profit", "tp")),
            strategy_id=self._to_str(self._get_first(payload, "strategy_id", "magic")),
            cluster=self._to_str(self._get_first(payload, "cluster"))
            or symbol_to_cluster.get(symbol),
            metadata=self._strip_known_keys(
                payload,
                {
                    "symbol",
                    "Symbol",
                    "lots",
                    "volume",
                    "Volume",
                    "side",
                    "type",
                    "entry_price",
                    "price_open",
                    "stop_loss",
                    "sl",
                    "take_profit",
                    "tp",
                    "strategy_id",
                    "magic",
                    "cluster",
                },
            ),
        )

    def _normalize_symbol_specs(
        self,
        symbol_specs: Dict[str, Any],
        positions: List[PositionState],
    ) -> Dict[str, SymbolState]:
        symbols = set(symbol_specs.keys()) | {position.symbol for position in positions}
        out: Dict[str, SymbolState] = {}

        for symbol in symbols:
            spec = symbol_specs.get(symbol)
            if isinstance(spec, SymbolState):
                out[symbol] = spec
                continue

            payload = self._to_dict(spec)
            out[symbol] = SymbolState(
                symbol=symbol,
                contract_size=self._to_float(
                    self._get_first(payload, "contract_size", "trade_contract_size")
                ),
                tick_value=self._to_float(
                    self._get_first(payload, "tick_value", "trade_tick_value")
                ),
                tick_size=self._to_float(
                    self._get_first(payload, "tick_size", "trade_tick_size")
                ),
                volume_min=self._to_float(
                    self._get_first(payload, "volume_min", "lots_min", "volume_minimum")
                ),
                volume_max=self._to_float(
                    self._get_first(payload, "volume_max", "lots_max", "volume_maximum")
                ),
                volume_step=self._to_float(
                    self._get_first(payload, "volume_step", "lots_step")
                ),
                currency_base=self._to_str(
                    self._get_first(payload, "currency_base", "base_currency")
                ),
                currency_profit=self._to_str(
                    self._get_first(payload, "currency_profit", "profit_currency")
                ),
                metadata=self._strip_known_keys(
                    payload,
                    {
                        "contract_size",
                        "trade_contract_size",
                        "tick_value",
                        "trade_tick_value",
                        "tick_size",
                        "trade_tick_size",
                        "volume_min",
                        "lots_min",
                        "volume_minimum",
                        "volume_max",
                        "lots_max",
                        "volume_maximum",
                        "volume_step",
                        "lots_step",
                        "currency_base",
                        "base_currency",
                        "currency_profit",
                        "profit_currency",
                    },
                ),
            )
        return out

    def _normalize_market_data(
        self,
        market_data: Dict[str, pd.DataFrame],
        timeframe: str,
    ) -> Dict[str, MarketState]:
        out: Dict[str, MarketState] = {}
        for symbol, bars in market_data.items():
            out[symbol] = MarketState(
                symbol=symbol,
                timeframe=timeframe,
                bars=bars.copy(),
                as_of=self._infer_as_of(bars),
            )
        return out

    def _compute_exposures(
        self,
        positions: List[PositionState],
        symbol_states: Dict[str, SymbolState],
        market_states: Dict[str, MarketState],
    ) -> Dict[str, float]:
        exposures: Dict[str, float] = {}

        for position in positions:
            spec = symbol_states.get(position.symbol)
            market = market_states.get(position.symbol)
            if spec is None or market is None:
                continue

            price = market.last_close
            if price is None:
                continue

            if spec.contract_size and spec.contract_size > 0:
                exposures[position.symbol] = float(position.lots * spec.contract_size * price)
            elif (
                spec.tick_value
                and spec.tick_value > 0
                and spec.tick_size
                and spec.tick_size > 0
            ):
                value_per_price_unit = spec.tick_value / spec.tick_size
                exposures[position.symbol] = float(position.lots * value_per_price_unit * price)

        return exposures

    def _infer_as_of(self, bars: pd.DataFrame) -> Optional[pd.Timestamp]:
        if isinstance(bars.index, pd.DatetimeIndex) and len(bars.index) > 0:
            return pd.Timestamp(bars.index[-1])
        return None

    def _normalize_side(self, raw_side: Any, lots: float) -> str:
        if raw_side is None:
            return "LONG" if lots >= 0 else "SHORT"
        token = str(raw_side).upper()
        if token in {"BUY", "LONG", "0"}:
            return "LONG"
        if token in {"SELL", "SHORT", "1"}:
            return "SHORT"
        return token

    def _to_dict(self, value: Any) -> Dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return dict(value)
        if is_dataclass(value):
            return asdict(value)

        out: Dict[str, Any] = {}
        for name in dir(value):
            if name.startswith("_"):
                continue
            try:
                attr = getattr(value, name)
            except Exception:
                continue
            if callable(attr):
                continue
            out[name] = attr
        return out

    def _get_first(self, payload: Dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in payload:
                return payload[key]
        return None

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    def _to_str(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value)
        return text if text else None

    def _strip_known_keys(
        self,
        payload: Dict[str, Any],
        known_keys: set[str],
    ) -> Dict[str, Any]:
        return {key: value for key, value in payload.items() if key not in known_keys}
