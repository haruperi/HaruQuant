"""Risk-Integrated Multi-Strategy Live Trading Engine.

Extends MultiStrategyEngine with full risk management cycle:
Market Data → Signals → Position Sizing → Regime Detection →
Allocation Planning → Risk Gating → Execution
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional, cast

import numpy as np
import pandas as pd

from apps.live.engine import MultiStrategyEngine, StrategyInstance
from apps.utils.logger import logger
from apps.risk.core import GovernanceEngine, PortfolioRiskEngine, PortfolioStateEngine
from apps.risk.limits import CorrelationPreference, RiskLimits
from apps.risk.optimization import AllocationPlanner
from apps.risk.position_sizing import PositionSizer
from apps.risk.regimes import RegimeState, RiskRegimeDetector


class RiskIntegratedEngine(MultiStrategyEngine):
    """Multi-strategy engine with institutional-grade risk management.

    Integrates:
    - Position Sizing (dynamic lot calculation)
    - Regime Detection (NORMAL vs STRESS)
    - Risk Budget Allocation (risk parity)
    - Governance Engine (hard constraints: VaR, ES, RC, cluster limits)
    """

    def __init__(self, config_path: str):
        """Initialize risk-integrated engine.

        Args:
            config_path: Path to configuration JSON with risk_management section
        """
        # Call parent constructor
        super().__init__(config_path)

        # Risk management components (will be initialized in initialize())
        self.risk_enabled = self.config.get("risk_management", {}).get("enabled", False)
        self.position_sizer: Optional[PositionSizer] = None
        self.regime_detector: Optional[RiskRegimeDetector] = None
        self.governance_engine: Optional[GovernanceEngine] = None
        self.risk_allocator: Optional[AllocationPlanner] = None
        self.portfolio_state_engine = PortfolioStateEngine()

        # Symbol clustering for cluster limits
        self.symbol_clusters: Dict[str, str] = self.config.get("symbol_clusters", {})

        # Current regime state
        self.current_regime: Optional[RegimeState] = None

        # Position sizing fallback
        self.fallback_volume = self.config.get("position_sizing", {}).get(
            "fallback_volume", 0.01
        )

        # Track equity curve for regime detection
        self.equity_curve: List[float] = []

        if self.risk_enabled:
            logger.info("Risk management ENABLED")
        else:
            logger.warning("Risk management DISABLED - using legacy portfolio manager")

    def initialize(self) -> bool:
        """Initialize engine with risk management components.

        Returns:
            True if successful
        """
        # First initialize base engine (MT5, strategies, etc.)
        if not super().initialize():
            return False

        # If risk management disabled, we're done
        if not self.risk_enabled:
            logger.info("Skipping risk management initialization (disabled)")
            return True

        try:
            logger.info("=" * 80)
            logger.info("Initializing Risk Management System")
            logger.info("=" * 80)

            # 1. Initialize Position Sizer
            logger.info("Initializing Position Sizer...")
            sizing_config = self.config.get("position_sizing", {})
            self.position_sizer = PositionSizer(
                method=sizing_config.get("method", "fixed_risk"),
                config=sizing_config.get("config", {"risk_percent": 1.0}),
                mt5_client=self.client,  # Pass MT5 client for dynamic stop loss
            )
            logger.info(
                f"Position Sizer: {self.position_sizer.method} - {self.position_sizer.config}"
            )
            if self.position_sizer.use_dynamic_stop_loss:
                logger.info(
                    f"Dynamic stop loss enabled: ATR({self.position_sizer.atr_period}) / {self.position_sizer.atr_target_devider}"
                )

            # 2. Initialize Regime Detector
            logger.info("Initializing Regime Detector...")
            regime_config = self.config["risk_management"].get("regime_detector", {})
            self.regime_detector = RiskRegimeDetector(
                vol_spike_mult=regime_config.get("vol_spike_mult", 1.8),
                corr_spike_level=regime_config.get("corr_spike_level", 0.55),
                dd_trigger_frac=regime_config.get("dd_trigger_frac", 0.05),
                lookback=regime_config.get("lookback", 60),
            )
            logger.info(f"Regime Detector configured: {regime_config}")

            # 3. Initialize Risk Limits
            logger.info("Initializing Risk Limits...")
            limits_config = self.config["risk_management"]["limits"]
            risk_limits = RiskLimits(
                var_cap_frac=limits_config.get("var_cap_frac", 0.10),
                es_cap_frac=limits_config.get("es_cap_frac", 0.15),
                delta_var_cap_frac=limits_config.get("delta_var_cap_frac", 0.02),
                delta_es_cap_frac=limits_config.get("delta_es_cap_frac", 0.03),
                max_margin_used_frac=limits_config.get("max_margin_used_frac", 0.50),
                min_pair_corr=limits_config.get("min_pair_corr", 0.20),
                stressed_corr_floor=limits_config.get("stressed_corr_floor", 0.60),
                use_stressed_corr=limits_config.get("use_stressed_corr", True),
                confidence_level=limits_config.get("confidence_level", 0.95),
                time_horizon_days=limits_config.get("time_horizon_days", 1),
                vol_lookback=limits_config.get("vol_lookback", 20),
                corr_lookback=limits_config.get("corr_lookback", 60),
                max_single_rc_frac=limits_config.get("max_single_rc_frac", 0.20),
                rc_rebalance_tolerance=limits_config.get(
                    "rc_rebalance_tolerance", 0.05
                ),
                cluster_var_caps=limits_config.get("cluster_var_caps"),
                cluster_es_caps=limits_config.get("cluster_es_caps"),
            )
            logger.info(
                f"Risk Limits: VaR={risk_limits.var_cap_frac:.1%}, ES={risk_limits.es_cap_frac:.1%}"
            )

            # 4. Initialize Governance Engine
            logger.info("Initializing Governance Engine...")
            if not self.client:
                logger.error("MT5 client not initialized")
                return False

            gov_config = self.config["risk_management"].get("governor_config", {})
            self.governance_engine = GovernanceEngine(
                risk_engine=PortfolioRiskEngine(
                    mt5_client=self.client,
                    timeframe=gov_config.get("timeframe", "D1"),
                    start_pos=gov_config.get("start_pos", 0),
                    end_pos=gov_config.get("end_pos", 500),
                ),
                limits=risk_limits,
            )
            logger.info("Governance Engine initialized")

            # 5. Initialize Risk Budget Allocator
            logger.info("Initializing Risk Budget Allocator...")
            corr_pref_config = self.config["risk_management"].get(
                "correlation_preference", {}
            )
            corr_pref = CorrelationPreference(
                target_corr=corr_pref_config.get("target_corr", 0.50),
                penalty_strength=corr_pref_config.get("penalty_strength", 2.0),
                min_budget_frac=corr_pref_config.get("min_budget_frac", 0.30),
            )
            self.risk_allocator = AllocationPlanner(self.governance_engine, corr_pref)
            logger.info("Risk Budget Allocator initialized")

            # 6. Initialize equity curve for regime detection
            if self.account:
                self.equity_curve = [float(self.account.Equity())]
                logger.info(f"Initial equity: ${self.equity_curve[0]:,.2f}")

            logger.info("=" * 80)
            logger.info("Risk Management System Initialized Successfully")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"Risk management initialization failed: {e}", exc_info=True)
            return False

    def _run_iteration(self):
        """Run iteration with risk management cycle.

        Flow:
        1. Check state (enabled/paused)
        2. Update equity curve & detect regime
        3. Collect signals from all strategies
        4. Calculate base position sizes
        5. Run risk budget allocation
        6. Gate each position through governance engine
        7. Execute approved trades
        """
        # 1. Check state
        if not self.state_manager:
            return

        if not self.state_manager.is_enabled():
            logger.debug("Trading disabled via state file")
            time.sleep(5)
            return

        if self.state_manager.is_paused():
            logger.debug("Trading paused via state file")
            time.sleep(5)
            return

        # 2. Update equity curve and detect regime (if risk enabled)
        if self.risk_enabled:
            self._update_regime()

        # 3. Refresh portfolio positions
        if self.portfolio_manager:
            self.portfolio_manager.refresh_all_positions()

        # 4-7. Process strategies with risk management
        if self.risk_enabled:
            self._process_strategies_with_risk()
        else:
            # Fallback to legacy processing (parent class method)
            for instance in self.strategies:
                self._process_strategy(instance)

        # Update state
        if self.state_manager:
            self.state_manager.update_last_run()

        # Export status
        self._export_status()

        # Sleep
        time.sleep(2)

    def _update_regime(self):
        """Update equity curve and detect market regime."""
        try:
            if not self.account or not self.regime_detector:
                return

            # Update equity curve
            current_equity = float(self.account.Equity())
            self.equity_curve.append(current_equity)

            # Keep only last 200 points for regime detection
            if len(self.equity_curve) > 200:
                self.equity_curve = self.equity_curve[-200:]

            # Build returns dataframe from all symbols
            returns_df = self._build_portfolio_returns()

            if returns_df is None or returns_df.empty:
                logger.debug("Insufficient data for regime detection")
                return

            # Detect regime
            equity_series = pd.Series(self.equity_curve)
            self.current_regime = self.regime_detector.detect(returns_df, equity_series)

            logger.info(f"Current Regime: {self.current_regime.name}")

        except Exception as e:
            logger.error(f"Error updating regime: {e}", exc_info=True)

    def _build_portfolio_returns(self) -> Optional[pd.DataFrame]:
        """Build returns dataframe from all traded symbols.

        Returns:
            DataFrame with returns for each symbol (columns = symbols)
        """
        try:
            if not self.client:
                return None

            # Get unique symbols from strategies
            symbols = list({inst.symbol for inst in self.strategies})

            if not symbols:
                return None

            # Fetch data for each symbol
            returns_dict = {}
            for symbol in symbols:
                try:
                    # Fetch data for regime detection (using H4 instead of D1)
                    # H4 data is more reliably available on demo accounts
                    df = self.client.get_bars(
                        symbol=symbol, timeframe="H4", count=500, start_pos=0
                    )

                    if df is None or df.empty or "close" not in df.columns:
                        continue

                    # Calculate log returns
                    prices = df["close"].astype(float)
                    returns = np.log(prices / prices.shift(1))
                    returns_dict[symbol] = returns

                except Exception as e:
                    logger.debug(f"Error fetching data for {symbol}: {e}")
                    continue

            if not returns_dict:
                return None

            # Combine into DataFrame
            returns_df = pd.DataFrame(returns_dict)
            returns_df = returns_df.dropna(how="all")

            return returns_df

        except Exception as e:
            logger.error(f"Error building returns dataframe: {e}", exc_info=True)
            return None

    def _process_strategies_with_risk(self):
        """Process all strategies with risk management cycle.

        Steps:
        1. Collect all signals from strategies
        2. Calculate base position sizes for each signal
        3. Run risk budget allocation
        4. Gate through governance engine
        5. Execute approved trades
        """
        try:
            # 1. Collect signals
            pending_signals: List[Dict[str, Any]] = []

            for instance in self.strategies:
                # Check for new bar
                if not instance.bar_monitor.check_new_bar():
                    continue

                # Get last closed bar
                last_bar = instance.bar_monitor.get_last_closed_bar()
                if last_bar is None:
                    continue

                logger.info(f"[{instance.name}] New bar closed: {last_bar.name}")

                # Process signal
                raw_signal = instance.signal_processor.update_with_new_bar(last_bar)
                if raw_signal:
                    signal = dict(raw_signal)
                    signal["_instance"] = instance
                    pending_signals.append(signal)

            if not pending_signals:
                return

            logger.info(f"Collected {len(pending_signals)} signals")

            # 2. Calculate base position sizes
            logger.info("Calculating base position sizes...")
            sized_signals = self._calculate_position_sizes(pending_signals)

            # 3. Filter to entry signals only for allocation
            entry_signals = [
                s
                for s in sized_signals
                if s["signal"] in ["buy", "sell", "Buy", "Sell"]
            ]

            if entry_signals:
                # 4. Run risk budget allocation
                logger.info("Running risk budget allocation...")
                allocated_signals = self._allocate_risk_budgets(entry_signals)
            else:
                allocated_signals = []

            # Combine allocated entries with exit signals (no allocation needed)
            exit_signals = [
                s
                for s in sized_signals
                if s["signal"] not in ["buy", "sell", "Buy", "Sell"]
            ]
            all_signals = allocated_signals + exit_signals

            # 5. Gate and execute
            for signal in all_signals:
                instance = cast(StrategyInstance, signal["_instance"])
                self._gate_and_execute(instance, signal)

        except Exception as e:
            logger.error(
                f"Error in risk-managed strategy processing: {e}", exc_info=True
            )

    def _calculate_position_sizes(
        self, signals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate position size for each signal.

        Args:
            signals: List of signal dictionaries

        Returns:
            List of signals with 'volume' field added
        """
        sized_signals = []

        for signal in signals:
            try:
                instance = signal["_instance"]

                # Get account balance
                account_balance = (
                    float(self.account.Equity()) if self.account else 10000.0
                )

                # Get symbol info
                symbol_info = None
                if self.client:
                    symbol_info = self.client.symbol_info(instance.symbol)

                # Calculate size
                if self.position_sizer:
                    volume = self.position_sizer.calculate_size(
                        account_balance=account_balance,
                        entry_price=signal.get("entry_price", 0),
                        stop_loss=signal.get("stop_loss"),
                        symbol_info=symbol_info,
                        context=signal,  # Pass full signal (may have ATR, etc.)
                        symbol=instance.symbol,  # Pass symbol for dynamic stop loss
                        signal_type=signal.get("signal"),  # Pass signal type (buy/sell)
                    )
                else:
                    volume = self.fallback_volume

                # Add volume to signal
                signal["volume"] = volume
                sized_signals.append(signal)

                logger.info(
                    f"[{instance.name}] Calculated volume: {volume:.3f} lots "
                    f"(balance=${account_balance:,.2f})"
                )

            except Exception as e:
                logger.error(f"Error calculating position size: {e}", exc_info=True)
                signal["volume"] = self.fallback_volume
                sized_signals.append(signal)

        return sized_signals

    def _allocate_risk_budgets(
        self, signals: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Allocate risk budgets using AllocationPlanner.

        Args:
            signals: List of entry signals with base volumes

        Returns:
            List of signals with adjusted volumes
        """
        try:
            if not self.risk_allocator:
                return signals

            # Build base_lots dict from signals
            base_lots = {}
            signal_map = {}  # symbol -> signal

            for signal in signals:
                instance = signal["_instance"]
                symbol = instance.symbol
                base_lots[symbol] = signal["volume"]
                signal_map[symbol] = signal

            symbols = list(base_lots.keys())

            # Get risk budgets from strategy configs
            budgets = {}
            for signal in signals:
                instance = signal["_instance"]
                budgets[instance.symbol] = instance.config.get("risk_budget", 1.0)

            # Run allocation
            logger.info(f"Base lots: {base_lots}")
            logger.info(f"Risk budgets: {budgets}")

            target_lots = self.risk_allocator.compute_target_lots(
                symbols=symbols,
                base_lots=base_lots,
                budgets=budgets,
                regime=self.current_regime,
            )

            logger.info(f"Allocated lots: {target_lots}")

            # Update signal volumes
            allocated_signals = []
            for symbol, target_volume in target_lots.items():
                if symbol in signal_map:
                    signal = signal_map[symbol]
                    old_volume = signal["volume"]
                    normalized_volume = self._normalize_volume(
                        signal["_instance"], target_volume
                    )
                    signal["volume"] = normalized_volume
                    allocated_signals.append(signal)

                    logger.info(
                        f"[{signal['_instance'].name}] Volume adjusted: "
                        f"{old_volume:.3f} → {normalized_volume:.3f} lots"
                    )

            return allocated_signals

        except Exception as e:
            logger.error(f"Error in risk allocation: {e}", exc_info=True)
            return signals  # Return original if allocation fails

    def _normalize_volume(self, instance: StrategyInstance, volume: float) -> float:
        """Normalize volume to symbol min/max/step constraints."""
        try:
            symbol_info = (
                instance.safety_checker.symbol_info if instance.safety_checker else None
            )
            if not symbol_info:
                return volume

            min_vol = float(getattr(symbol_info, "volume_min", 0.0) or 0.0)
            max_vol = float(getattr(symbol_info, "volume_max", 0.0) or 0.0)
            step_vol = float(getattr(symbol_info, "volume_step", 0.0) or 0.0)

            if step_vol > 0:
                steps = round((volume - min_vol) / step_vol)
                volume = min_vol + steps * step_vol

            volume = max(min_vol, min(volume, max_vol))
            return float(volume)
        except Exception as e:
            logger.warning(f"[{instance.name}] Volume normalize failed: {e}")
            return volume

    def _gate_and_execute(self, instance: StrategyInstance, signal: Dict[str, Any]):
        """Gate signal through governance engine and execute if approved.

        Args:
            instance: Strategy instance
            signal: Signal dictionary with volume
        """
        try:
            # Log signal
            self._log_signal(instance, signal)

            # Refresh positions
            instance.position_manager.refresh_positions()

            # For exit signals, skip governance checks (always allow exits)
            if signal["signal"] in [
                "close buy",
                "close sell",
                "Close Buy",
                "Close Sell",
            ]:
                logger.info(f"[{instance.name}] Exit signal - bypassing governance engine")
                self._execute_trade(instance, signal)
                return

            # Validate with basic safety checks first
            if not self._validate_signal(instance, signal):
                return

            # Gate through governance engine
            if not self._risk_governance_gate(instance, signal):
                return

            # Execute trade
            self._execute_trade(instance, signal)

        except Exception as e:
            logger.error(f"Error in gate_and_execute: {e}", exc_info=True)

    def _risk_governance_gate(
        self, instance: StrategyInstance, signal: Dict[str, Any]
    ) -> bool:
        """Gate signal through governance engine.

        Args:
            instance: Strategy instance
            signal: Signal dictionary

        Returns:
            True if approved, False if rejected
        """
        try:
            if not self.governance_engine:
                return True  # No governance engine, allow

            logger.info(f"[{instance.name}] Gating through Governance Engine...")

            # Get current portfolio positions (all strategies)
            current_positions = self._get_portfolio_positions()

            # Determine position delta
            candidate_lots = signal.get("volume", 0.01)
            if signal["signal"].lower() == "sell":
                candidate_lots = -candidate_lots  # Short position

            risk_engine = self.governance_engine.risk_engine
            current_state = self.portfolio_state_engine.build_state_from_engine(
                engine=self,
                symbols=sorted(set(current_positions.keys()) | {str(instance.symbol)}),
                timeframe=risk_engine.timeframe,
                count=max(int(risk_engine.end_pos - risk_engine.start_pos), 1),
                start_pos=int(risk_engine.start_pos),
                positions=current_positions,
                account=self.account_info(),
                limits=self.governance_engine.limits,
                symbol_to_cluster=self.symbol_clusters,
                metadata={"source": "live_risk_governance"},
            )

            # Evaluate through governance engine
            report = self.governance_engine.evaluate_add_position_from_state(
                current_state=current_state,
                candidate_symbol=instance.symbol,
                candidate_lots=candidate_lots,
                regime=self.current_regime,
            )

            # Log report
            logger.info("=" * 60)
            logger.info(f"Governance Engine Decision: {report.decision}")
            logger.info(f"Reason: {report.reason}")
            logger.info(f"Current VaR: ${report.current_var:,.2f}")
            logger.info(f"New VaR: ${report.new_var:,.2f}")
            logger.info(f"Delta VaR: ${report.delta_var:,.2f}")
            logger.info(f"Current ES: ${report.current_es:,.2f}")
            logger.info(f"New ES: ${report.new_es:,.2f}")
            logger.info(f"Delta ES: ${report.delta_es:,.2f}")
            if report.rc_map_new:
                logger.info(f"Risk Contributions: {report.rc_map_new}")
            logger.info("=" * 60)

            if report.decision == "REJECT":
                logger.warning(f"[{instance.name}] Trade REJECTED by Governance Engine")
                if self.notifier:
                    self.notifier.notify_safety_violation(
                        f"[{instance.name}] Governance Engine: {report.reason}"
                    )
                return False

            logger.info(f"[{instance.name}] Trade APPROVED by Governance Engine")
            return True

        except Exception as e:
            logger.error(f"Error in governance engine gate: {e}", exc_info=True)
            # Fail safe: reject if error
            return False

    def _get_portfolio_positions(self) -> Dict[str, float]:
        """Get current portfolio positions across all strategies.

        Returns:
            Dictionary of {symbol: total_lots}
        """
        positions: Dict[str, float] = {}

        for instance in self.strategies:
            instance.position_manager.refresh_positions()

            # Sum up positions for this symbol
            for pos in instance.position_manager.get_all_positions():
                symbol = instance.symbol
                volume = pos.get("volume", 0.0)
                position_type = pos.get("type", 0)  # 0=buy, 1=sell

                # Convert to signed lots (positive=long, negative=short)
                lots = volume if position_type == 0 else -volume

                positions[symbol] = positions.get(symbol, 0.0) + lots

        return positions

    def get_status(self) -> Dict:
        """Get engine status including risk management state.

        Returns:
            Status dictionary
        """
        status = super().get_status()

        if self.risk_enabled:
            status["risk_management"] = {
                "enabled": True,
                "current_regime": (
                    self.current_regime.name if self.current_regime else "UNKNOWN"
                ),
                "equity_curve_length": len(self.equity_curve),
                "position_sizing_method": (
                    self.position_sizer.method if self.position_sizer else None
                ),
            }
        else:
            status["risk_management"] = {"enabled": False}

        return status

    def _execute_trade(self, instance: StrategyInstance, signal: Dict[str, Any]):
        """Execute trade with risk-adjusted volume.

        Args:
            instance: Strategy instance
            signal: Signal with volume
        """
        # Override volume in trade executor temporarily
        original_volume = instance.trade_executor.volume
        instance.trade_executor.volume = signal.get("volume", original_volume)

        try:
            # Execute
            success, message = instance.trade_executor.execute_signal(signal)

            # Update statistics
            if success:
                instance.trades_executed += 1
                instance.last_trade_time = datetime.now()
                if self.state_manager:
                    self.state_manager.increment_trade_count()
                    trade_count = self.state_manager.get_trade_count_today()
                    logger.info(f"Total trades today: {trade_count}")
            else:
                instance.trades_failed += 1

            # Notify
            if self.notifier:
                notification_signal = signal.copy()
                notification_signal["symbol"] = instance.symbol
                notification_signal["strategy_name"] = instance.name
                self.notifier.notify_signal(
                    notification_signal,
                    executed=success,
                    error=message if not success else None,
                )

            logger.info("=" * 60)

        finally:
            # Restore original volume
            instance.trade_executor.volume = original_volume

