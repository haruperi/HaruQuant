"""Risk API routes."""

from io import StringIO
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field
import numpy as np
import pandas as pd

from backend.api.auth_utils import get_user_id_from_token
from backend.common.logger import logger
from backend.services.risk_engine import (
    AllocationPlanner,
    CorrelationPreference,
    GovernanceEngine,
    PortfolioRiskEngine,
    PortfolioStateEngine,
    PositionSizer,
    RegimeState,
    RiskLimits,
)
from backend.services.risk_engine.models import AccountState, MarketState, PortfolioState, PositionState, SymbolState
from backend.services.risk_engine.regimes import CrisisRegimeDetector, RegimeEngine
from backend.services.simulation.engine import Engine

router = APIRouter()
AUTH_HEADER = Header(None)
state_engine = PortfolioStateEngine()

SizingMethod = Literal[
    "fixed_lot",
    "milestone",
    "fixed_risk",
    "kelly",
    "volatility",
    "fixed_fractional",
]


class PositionSizingRequest(BaseModel):
    method: SizingMethod
    account_balance: float = Field(gt=0)
    entry_price: float = Field(gt=0)
    stop_loss: Optional[float] = None
    signal_type: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class PositionSizingResponse(BaseModel):
    method: SizingMethod
    size: float
    normalized_inputs: Dict[str, Any]


RegimeMode = Literal["crisis", "full"]
RegimeSource = Literal["mt5", "manual"]


class RegimeDetectionRequest(BaseModel):
    source: RegimeSource = "mt5"
    mode: RegimeMode = "crisis"
    symbols: List[str] = Field(default_factory=list)
    timeframe: str = "H1"
    bar_count: int = Field(default=300, ge=20)
    returns_csv: Optional[str] = None
    equity_curve: Optional[str] = None
    spread_bps: Optional[float] = Field(default=2.0, ge=0.0)
    vol_spike_mult: float = Field(default=1.8, gt=0.0)
    corr_spike_level: float = Field(default=0.55)
    dd_trigger_frac: float = Field(default=0.05, ge=0.0)
    lookback: int = Field(default=60, ge=5)


class RegimeStatePayload(BaseModel):
    name: str
    family: str
    confidence: float
    signals_triggered: List[str]
    warnings: List[str]
    metadata: Dict[str, Any]


class RegimeSignalPayload(BaseModel):
    signal_key: str
    triggered: bool
    observed_value: Optional[float] = None
    threshold_value: Optional[float] = None
    message: str = ""


class RegimeDetectionResponse(BaseModel):
    source: RegimeSource
    mode: RegimeMode
    current: RegimeStatePayload
    market: Optional[RegimeStatePayload] = None
    volatility: Optional[RegimeStatePayload] = None
    liquidity: Optional[RegimeStatePayload] = None
    crisis: Optional[RegimeStatePayload] = None
    signals: List[RegimeSignalPayload] = Field(default_factory=list)
    transition: Optional[Dict[str, Any]] = None


class RiskAllocationRequest(BaseModel):
    symbols: List[str] = Field(default_factory=list)
    timeframe: str = "H1"
    bar_count: int = Field(default=200, ge=20)
    base_lots: Dict[str, float] = Field(default_factory=dict)
    budgets: Dict[str, float] = Field(default_factory=dict)
    regime_name: Optional[str] = None
    corr_target: float = Field(default=0.50)
    corr_penalty_strength: float = Field(default=2.0, ge=0.0)
    corr_min_budget_frac: float = Field(default=0.30, ge=0.0)


class RiskAllocationResponse(BaseModel):
    symbols: List[str]
    timeframe: str
    bar_count: int
    target_lots: Dict[str, float]
    deltas: Dict[str, float]
    normalized_budgets: Dict[str, float]


class GovernanceEventPayload(BaseModel):
    rule_key: str
    severity: str
    message: str
    observed_value: Optional[float] = None
    threshold_value: Optional[float] = None
    scope: str = "portfolio"
    scope_key: Optional[str] = None


class GovernanceReportPayload(BaseModel):
    decision: str
    reason: str
    current_var: float
    new_var: float
    delta_var: float
    current_es: float
    new_es: float
    delta_es: float
    current_margin_used: Optional[float] = None
    new_margin_used: Optional[float] = None
    compliance_status: Optional[str] = None
    warnings: List[GovernanceEventPayload] = Field(default_factory=list)
    breaches: List[GovernanceEventPayload] = Field(default_factory=list)


class GovernanceRequest(BaseModel):
    symbols: List[str] = Field(default_factory=list)
    timeframe: str = "H1"
    bar_count: int = Field(default=200, ge=20)
    current_positions: Dict[str, float] = Field(default_factory=dict)
    candidate_symbol: str
    candidate_lots: float
    regime_name: Optional[str] = None
    var_cap_frac: float = Field(default=0.10, gt=0.0)
    es_cap_frac: float = Field(default=0.15, gt=0.0)
    delta_var_cap_frac: float = Field(default=0.02, gt=0.0)
    delta_es_cap_frac: float = Field(default=0.03, gt=0.0)
    max_margin_used_frac: float = Field(default=0.50, gt=0.0)
    max_single_rc_frac: float = Field(default=0.20, gt=0.0)


class GovernanceResponse(BaseModel):
    symbols: List[str]
    timeframe: str
    bar_count: int
    current_report: GovernanceReportPayload
    candidate_report: GovernanceReportPayload


class _RiskApiClientAdapter:
    """Small adapter to normalize MT5 client methods expected by risk engines."""

    def __init__(self, client):
        self.client = client

    def get_bars(self, symbol: str, timeframe: str, count: int = 100, start_pos: int = 0):
        return self.client.get_bars(
            symbol=symbol,
            timeframe=timeframe,
            count=count,
            start_pos=start_pos,
        )

    def get_symbol_info(self, symbol: str):
        if hasattr(self.client, "get_symbol_info"):
            return self.client.get_symbol_info(symbol)
        if hasattr(self.client, "symbol_info"):
            return self.client.symbol_info(symbol)
        return None

    def get_account_equity(self) -> float:
        account = self.client.account_info()
        if account is None:
            return 0.0
        return float(getattr(account, "equity", 0.0) or 0.0)

    def get_margin_required(self, symbol: str, lots: float):
        info = self.get_symbol_info(symbol)
        if info is None or not hasattr(self.client, "order_calc_margin"):
            return None
        ask = float(getattr(info, "ask", 0.0) or 0.0)
        bid = float(getattr(info, "bid", 0.0) or 0.0)
        price = ask if ask > 0.0 else bid
        if price <= 0.0:
            return None
        margin_required = self.client.order_calc_margin(
            0,
            str(symbol),
            abs(float(lots)),
            price,
        )
        return None if margin_required is None else float(margin_required)

    def get_peak_equity(self):
        return None


@router.post(
    "/position-sizing",
    response_model=PositionSizingResponse,
    status_code=status.HTTP_200_OK,
)
async def calculate_position_size(
    request: PositionSizingRequest,
) -> PositionSizingResponse:
    """Calculate position size using the Python risk PositionSizer."""
    try:
        logger.info(
            "Risk API position sizing request",
            extra={"component": "api.risk", "method": request.method},
        )
        sizer = PositionSizer(method=request.method, config=request.config)
        size = sizer.calculate_size(
            account_balance=request.account_balance,
            entry_price=request.entry_price,
            stop_loss=request.stop_loss,
            symbol_info=None,
            context=request.context,
            signal_type=request.signal_type,
        )
    except ValueError as exc:
        logger.warning(
            "Risk API position sizing validation failed",
            extra={"component": "api.risk", "method": request.method, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Risk API position sizing failed",
            extra={"component": "api.risk", "method": request.method, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate position size: {exc}",
        ) from exc

    return PositionSizingResponse(
        method=request.method,
        size=float(size),
        normalized_inputs={
            "account_balance": request.account_balance,
            "entry_price": request.entry_price,
            "stop_loss": request.stop_loss,
            "signal_type": request.signal_type,
            "config": request.config,
            "context": request.context,
        },
    )


@router.post(
    "/regime-detection",
    response_model=RegimeDetectionResponse,
    status_code=status.HTTP_200_OK,
)
async def detect_regime(
    request: RegimeDetectionRequest,
    authorization: str = AUTH_HEADER,
) -> RegimeDetectionResponse:
    """Run crisis-only or full regime detection from pasted returns input."""
    try:
        logger.info(
            "Risk API regime detection request",
            extra={
                "component": "api.risk",
                "source": request.source,
                "mode": request.mode,
                "symbols": ",".join(request.symbols),
                "timeframe": request.timeframe,
                "bar_count": request.bar_count,
            },
        )
        equity_curve = _parse_optional_series(request.equity_curve)
        if request.source == "mt5":
            get_user_id_from_token(authorization)
            real_state = _build_real_portfolio_state(
                symbols=request.symbols,
                timeframe=request.timeframe,
                bar_count=request.bar_count,
            )
            returns_df = _build_returns_from_market_state(real_state)
        else:
            returns_df = _parse_returns_csv(request.returns_csv)
            real_state = _build_synthetic_portfolio_state(
                returns_df=returns_df,
                spread_bps=float(request.spread_bps or 0.0),
                equity_curve=equity_curve,
            )
    except ValueError as exc:
        logger.warning(
            "Risk API regime detection validation failed",
            extra={"component": "api.risk", "source": request.source, "mode": request.mode, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Risk API regime detection failed",
            extra={"component": "api.risk", "source": request.source, "mode": request.mode, "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to detect regime: {exc}",
        ) from exc

    crisis_detector = CrisisRegimeDetector(
        vol_spike_mult=request.vol_spike_mult,
        corr_spike_level=request.corr_spike_level,
        dd_trigger_frac=request.dd_trigger_frac,
        lookback=request.lookback,
    )

    if request.mode == "crisis":
        state, signals = crisis_detector.detect_with_signals(returns_df, equity_curve)
        return RegimeDetectionResponse(
            source=request.source,
            mode=request.mode,
            current=_to_state_payload(state),
            crisis=_to_state_payload(state),
            signals=[_to_signal_payload(signal) for signal in signals],
        )

    report = RegimeEngine(crisis_detector=crisis_detector).evaluate_state(
        real_state,
        equity_curve=equity_curve,
    )
    return RegimeDetectionResponse(
        source=request.source,
        mode=request.mode,
        current=_to_state_payload(report.current),
        market=_to_state_payload(report.market),
        volatility=_to_state_payload(report.volatility),
        liquidity=_to_state_payload(report.liquidity),
        crisis=_to_state_payload(report.crisis),
        transition={
            "changed": report.transition.changed,
            "previous_name": report.transition.previous_name,
            "current_name": report.transition.current_name,
        },
        signals=[_to_signal_payload(signal) for signal in report.signals],
    )


@router.post(
    "/allocation",
    response_model=RiskAllocationResponse,
    status_code=status.HTTP_200_OK,
)
async def calculate_risk_allocation(
    request: RiskAllocationRequest,
    authorization: str = AUTH_HEADER,
) -> RiskAllocationResponse:
    """Compute target lots and deltas using the live AllocationPlanner."""
    engine: Optional[Engine] = None
    try:
        logger.info(
            "Risk API allocation request",
            extra={
                "component": "api.risk",
                "symbols": ",".join(request.symbols),
                "timeframe": request.timeframe,
                "bar_count": request.bar_count,
                "regime_name": request.regime_name or "",
            },
        )
        get_user_id_from_token(authorization)
        clean_symbols = [str(symbol).strip().upper() for symbol in request.symbols if str(symbol).strip()]
        if not clean_symbols:
            raise ValueError("At least one symbol is required.")

        clean_base_lots = {
            symbol: float(request.base_lots.get(symbol, 0.0))
            for symbol in clean_symbols
        }
        if not any(abs(lot) > 0 for lot in clean_base_lots.values()):
            raise ValueError("At least one non-zero base lot is required.")

        normalized_budgets = _normalize_budgets(
            clean_symbols,
            request.budgets,
        )

        engine = Engine(backend="sim")
        if not hasattr(engine.client, "get_symbol_info") and hasattr(engine.client, "symbol_info"):
            engine.client.get_symbol_info = engine.client.symbol_info  # type: ignore[attr-defined]
        risk_client = _RiskApiClientAdapter(engine.client)
        governance_engine = GovernanceEngine(
            risk_engine=PortfolioRiskEngine(
                mt5_client=risk_client,
                timeframe=request.timeframe,
                start_pos=0,
                end_pos=request.bar_count,
            ),
            limits=RiskLimits(),
        )
        planner = AllocationPlanner(
            governance_engine,
            CorrelationPreference(
                target_corr=float(request.corr_target),
                penalty_strength=float(request.corr_penalty_strength),
                min_budget_frac=float(request.corr_min_budget_frac),
            ),
        )
        regime = (
            RegimeState(name=str(request.regime_name).upper())
            if request.regime_name and str(request.regime_name).strip()
            else None
        )
        target_lots = planner.compute_target_lots(
            symbols=clean_symbols,
            base_lots=clean_base_lots,
            budgets=normalized_budgets or None,
            regime=regime,
        )
        deltas = planner.lots_to_deltas(clean_base_lots, target_lots)
    except ValueError as exc:
        logger.warning(
            "Risk API allocation validation failed",
            extra={"component": "api.risk", "symbols": ",".join(request.symbols), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Risk API allocation failed",
            extra={"component": "api.risk", "symbols": ",".join(request.symbols), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate risk allocation: {exc}",
        ) from exc
    finally:
        if engine is not None:
            engine.client.shutdown()

    return RiskAllocationResponse(
        symbols=clean_symbols,
        timeframe=request.timeframe,
        bar_count=request.bar_count,
        target_lots={symbol: float(target_lots.get(symbol, 0.0)) for symbol in clean_symbols},
        deltas={symbol: float(deltas.get(symbol, 0.0)) for symbol in clean_symbols},
        normalized_budgets=normalized_budgets,
    )


@router.post(
    "/governance",
    response_model=GovernanceResponse,
    status_code=status.HTTP_200_OK,
)
async def evaluate_risk_governance(
    request: GovernanceRequest,
    authorization: str = AUTH_HEADER,
) -> GovernanceResponse:
    """Evaluate current compliance and one candidate add-position check."""
    engine: Optional[Engine] = None
    try:
        logger.info(
            "Risk API governance request",
            extra={
                "component": "api.risk",
                "symbols": ",".join(request.symbols),
                "timeframe": request.timeframe,
                "bar_count": request.bar_count,
                "candidate_symbol": request.candidate_symbol,
                "candidate_lots": request.candidate_lots,
                "regime_name": request.regime_name or "",
            },
        )
        get_user_id_from_token(authorization)

        clean_symbols = [str(symbol).strip().upper() for symbol in request.symbols if str(symbol).strip()]
        if not clean_symbols:
            raise ValueError("At least one symbol is required.")

        candidate_symbol = str(request.candidate_symbol).strip().upper()
        if not candidate_symbol:
            raise ValueError("Candidate symbol is required.")
        if candidate_symbol not in clean_symbols:
            clean_symbols.append(candidate_symbol)

        current_positions = {
            str(symbol).strip().upper(): float(lots)
            for symbol, lots in request.current_positions.items()
            if str(symbol).strip() and abs(float(lots)) > 0
        }
        if not current_positions:
            raise ValueError("At least one current position is required.")

        engine = Engine(backend="sim")
        if not hasattr(engine.client, "get_symbol_info") and hasattr(engine.client, "symbol_info"):
            engine.client.get_symbol_info = engine.client.symbol_info  # type: ignore[attr-defined]

        risk_client = _RiskApiClientAdapter(engine.client)
        governance_limits = RiskLimits(
            var_cap_frac=float(request.var_cap_frac),
            es_cap_frac=float(request.es_cap_frac),
            delta_var_cap_frac=float(request.delta_var_cap_frac),
            delta_es_cap_frac=float(request.delta_es_cap_frac),
            max_margin_used_frac=float(request.max_margin_used_frac),
            max_single_rc_frac=float(request.max_single_rc_frac),
        )
        governance_engine = GovernanceEngine(
            risk_engine=PortfolioRiskEngine(
                mt5_client=risk_client,
                timeframe=request.timeframe,
                start_pos=0,
                end_pos=request.bar_count,
            ),
            limits=governance_limits,
        )
        regime = (
            RegimeState(name=str(request.regime_name).upper())
            if request.regime_name and str(request.regime_name).strip()
            else None
        )
        current_state = state_engine.build_state_from_engine(
            engine=engine,
            symbols=clean_symbols,
            timeframe=request.timeframe,
            count=request.bar_count,
            start_pos=0,
            positions=current_positions,
            limits=governance_limits,
            metadata={"source": "risk_api_governance"},
        )

        current_report = governance_engine.evaluate_portfolio_state(
            state=current_state,
            regime=regime,
        )
        candidate_report = governance_engine.evaluate_add_position_from_state(
            current_state=current_state,
            candidate_symbol=candidate_symbol,
            candidate_lots=float(request.candidate_lots),
            regime=regime,
        )
    except ValueError as exc:
        logger.warning(
            "Risk API governance validation failed",
            extra={"component": "api.risk", "symbols": ",".join(request.symbols), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception(
            "Risk API governance failed",
            extra={"component": "api.risk", "symbols": ",".join(request.symbols), "error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate risk governance: {exc}",
        ) from exc
    finally:
        if engine is not None:
            engine.client.shutdown()

    return GovernanceResponse(
        symbols=clean_symbols,
        timeframe=request.timeframe,
        bar_count=request.bar_count,
        current_report=_to_governance_payload(current_report),
        candidate_report=_to_governance_payload(candidate_report),
    )


def _parse_returns_csv(raw_csv: str) -> pd.DataFrame:
    text = (raw_csv or "").strip()
    if not text:
        raise ValueError("Returns CSV is required.")
    frame = pd.read_csv(StringIO(text))
    if frame.empty:
        raise ValueError("Returns CSV did not contain any rows.")

    if len(frame.columns) < 1:
        raise ValueError("Returns CSV must contain at least one symbol column.")

    # Drop a leading label column such as date/index if present and non-numeric.
    if not _column_is_numeric(frame.iloc[:, 0]):
        frame = frame.iloc[:, 1:]

    if frame.empty:
        raise ValueError("Returns CSV must contain numeric symbol columns.")

    numeric = frame.apply(pd.to_numeric, errors="coerce")
    numeric = numeric.dropna(how="all")
    if numeric.empty:
        raise ValueError("Returns CSV must contain numeric return values.")

    numeric.columns = [str(column) for column in numeric.columns]
    return numeric


def _normalize_budgets(
    symbols: List[str],
    budgets: Dict[str, float],
) -> Dict[str, float]:
    if not budgets:
        return {}

    filtered = {
        symbol: float(budgets.get(symbol, 0.0))
        for symbol in symbols
        if float(budgets.get(symbol, 0.0)) > 0
    }
    total = sum(filtered.values())
    if total <= 0:
        return {}
    return {symbol: value / total for symbol, value in filtered.items()}


def _parse_optional_series(raw_series: Optional[str]) -> Optional[pd.Series]:
    text = (raw_series or "").strip()
    if not text:
        return None
    parts = [chunk.strip() for chunk in text.replace("\n", ",").split(",")]
    values = [float(part) for part in parts if part]
    if not values:
        return None
    return pd.Series(values, dtype=float)


def _column_is_numeric(series: pd.Series) -> bool:
    converted = pd.to_numeric(series, errors="coerce")
    return bool(converted.notna().any())


def _build_synthetic_portfolio_state(
    returns_df: pd.DataFrame,
    spread_bps: float,
    equity_curve: Optional[pd.Series],
) -> PortfolioState:
    symbols = list(returns_df.columns)
    positions = [
        PositionState(symbol=symbol, lots=1.0, side="LONG")
        for symbol in symbols
    ]
    symbol_states = {
        symbol: SymbolState(symbol=symbol, contract_size=1.0)
        for symbol in symbols
    }
    spread_value = float(spread_bps) / 10000.0
    market_states = {
        symbol: MarketState(
            symbol=symbol,
            timeframe="UI",
            bars=_returns_to_market_bars(returns_df[symbol], spread_value),
        )
        for symbol in symbols
    }
    metadata: Dict[str, Any] = {}
    if equity_curve is not None:
        metadata["equity_curve"] = equity_curve

    return PortfolioState(
        account=AccountState(
            equity=float(equity_curve.iloc[-1]) if equity_curve is not None and not equity_curve.empty else 10000.0,
            balance=float(equity_curve.iloc[-1]) if equity_curve is not None and not equity_curve.empty else 10000.0,
            free_margin=float(equity_curve.iloc[-1]) if equity_curve is not None and not equity_curve.empty else 10000.0,
            margin_used=0.0,
            currency="USD",
        ),
        positions=positions,
        symbols=symbol_states,
        markets=market_states,
        metadata=metadata,
    )


def _build_real_portfolio_state(
    symbols: List[str],
    timeframe: str,
    bar_count: int,
) -> PortfolioState:
    clean_symbols = [str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()]
    if not clean_symbols:
        raise ValueError("At least one symbol is required for MT5 regime detection.")

    engine = Engine(backend="sim")
    markets: Dict[str, MarketState] = {}
    symbol_states: Dict[str, SymbolState] = {}
    positions: List[PositionState] = []

    for symbol in clean_symbols:
        bars = engine.client.get_bars(symbol=symbol, timeframe=timeframe, count=bar_count, start_pos=0)
        if bars is None or bars.empty:
            continue

        market_bars = bars.copy()
        if "close" in market_bars.columns and "Close" not in market_bars.columns:
            market_bars = market_bars.rename(columns={"close": "Close"})
        if "spread" in market_bars.columns and "Spread" not in market_bars.columns:
            market_bars = market_bars.rename(columns={"spread": "Spread"})

        markets[symbol] = MarketState(symbol=symbol, timeframe=timeframe, bars=market_bars)
        positions.append(PositionState(symbol=symbol, lots=1.0, side="LONG"))

        info = engine.client.symbol_info(symbol)
        symbol_states[symbol] = SymbolState(
            symbol=symbol,
            contract_size=float(getattr(info, "trade_contract_size", 1.0) or 1.0) if info is not None else 1.0,
            tick_value=float(getattr(info, "trade_tick_value", 0.0) or 0.0) if info is not None else 0.0,
            tick_size=float(getattr(info, "trade_tick_size", 0.0) or 0.0) if info is not None else 0.0,
            volume_min=float(getattr(info, "volume_min", 0.01) or 0.01) if info is not None else 0.01,
            volume_max=float(getattr(info, "volume_max", 100.0) or 100.0) if info is not None else 100.0,
            volume_step=float(getattr(info, "volume_step", 0.01) or 0.01) if info is not None else 0.01,
            currency_base=str(getattr(info, "currency_base", "") or None) if info is not None else None,
            currency_profit=str(getattr(info, "currency_profit", "") or None) if info is not None else None,
        )

    if not markets:
        raise ValueError("No MT5 bars were available for the selected symbols/timeframe.")

    return PortfolioState(
        account=AccountState(
            equity=10000.0,
            balance=10000.0,
            free_margin=10000.0,
            margin_used=0.0,
            currency="USD",
        ),
        positions=positions,
        symbols=symbol_states,
        markets=markets,
        metadata={"source": "mt5"},
    )


def _build_returns_from_market_state(state: PortfolioState) -> pd.DataFrame:
    cols: Dict[str, pd.Series] = {}
    for symbol, market in state.markets.items():
        bars = market.bars
        if bars.empty:
            continue
        close_col = "Close" if "Close" in bars.columns else "close"
        if close_col not in bars.columns:
            continue
        prices = bars[close_col].astype(float)
        cols[symbol] = np.log(prices / prices.shift(1))
    if not cols:
        return pd.DataFrame()
    return pd.DataFrame(cols).dropna(how="all")


def _returns_to_market_bars(returns: pd.Series, spread_value: float) -> pd.DataFrame:
    cleaned = pd.to_numeric(returns, errors="coerce").dropna().astype(float)
    if cleaned.empty:
        return pd.DataFrame(columns=["Close", "Spread"])
    price_path = np.exp(np.r_[0.0, cleaned.values].cumsum())
    bars = pd.DataFrame({"Close": price_path})
    bars["Spread"] = spread_value
    return bars


def _to_state_payload(state) -> RegimeStatePayload:
    return RegimeStatePayload(
        name=state.name,
        family=state.family,
        confidence=float(state.confidence),
        signals_triggered=list(state.signals_triggered),
        warnings=list(state.warnings),
        metadata=dict(state.metadata),
    )


def _to_signal_payload(signal) -> RegimeSignalPayload:
    return RegimeSignalPayload(
        signal_key=signal.signal_key,
        triggered=signal.triggered,
        observed_value=signal.observed_value,
        threshold_value=signal.threshold_value,
        message=signal.message,
    )


def _to_governance_event_payload(event) -> GovernanceEventPayload:
    return GovernanceEventPayload(
        rule_key=event.rule_key,
        severity=event.severity,
        message=event.message,
        observed_value=event.observed_value,
        threshold_value=event.threshold_value,
        scope=event.scope,
        scope_key=event.scope_key,
    )


def _to_governance_payload(report) -> GovernanceReportPayload:
    return GovernanceReportPayload(
        decision=report.decision,
        reason=report.reason,
        current_var=float(report.current_var),
        new_var=float(report.new_var),
        delta_var=float(report.delta_var),
        current_es=float(report.current_es),
        new_es=float(report.new_es),
        delta_es=float(report.delta_es),
        current_margin_used=None if report.current_margin_used is None else float(report.current_margin_used),
        new_margin_used=None if report.new_margin_used is None else float(report.new_margin_used),
        compliance_status=None if report.governance_state is None else str(report.governance_state.status),
        warnings=[_to_governance_event_payload(event) for event in (report.warnings or [])],
        breaches=[_to_governance_event_payload(event) for event in (report.breaches or [])],
    )
