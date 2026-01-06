"""Database schema management module."""

import os
import sqlite3

from apps.logger import logger


class SchemaManager:
    """Database schema initialization and management."""

    db_path: str

    def initialize_database(self) -> bool:
        """Initialize the database schema."""
        logger.info(f"Connecting to database at: {self.db_path}")

        conn = None
        try:
            # Connect to the database (creates it if it doesn't exist)
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")

            # =========================================================================
            # USER MANAGEMENT TABLES
            # =========================================================================

            # Create users table
            create_users_table_query = """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name VARCHAR(255),
                username VARCHAR(100) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                hashed_password VARCHAR(255) NOT NULL,
                encryption_key BLOB,
                is_active BOOLEAN DEFAULT 1,
                is_superuser BOOLEAN DEFAULT 0,
                is_verified BOOLEAN DEFAULT 0,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_users_table_query)

            # Create user_settings table
            create_user_settings_table_query = """
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                theme VARCHAR(20) DEFAULT 'system',
                language VARCHAR(10) DEFAULT 'en',
                timezone VARCHAR(50) DEFAULT 'UTC',
                log_verbosity VARCHAR(20) DEFAULT 'info',
                performance_mode VARCHAR(20) DEFAULT 'balanced',
                broker_credentials TEXT DEFAULT '{}',
                trading_preferences TEXT DEFAULT '{}',
                notifications TEXT DEFAULT '{}',
                alert_triggers TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_user_settings_table_query)

            # Create user_sessions table
            create_user_sessions_table_query = """
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token VARCHAR(255) NOT NULL UNIQUE,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expire_time TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_user_sessions_table_query)

            # Create strategies table
            create_strategies_table_query = """
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                status VARCHAR(20) DEFAULT 'inactive',
                category VARCHAR(50),
                is_public BOOLEAN DEFAULT 0,
                active_version_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_strategies_table_query)

            # Create strategy_versions table
            create_strategy_versions_table_query = """
            CREATE TABLE IF NOT EXISTS strategy_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                version VARCHAR(20) NOT NULL,
                file_path TEXT NOT NULL,
                parameters TEXT DEFAULT '{}',
                changelog TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (strategy_id) REFERENCES strategies (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL,
                UNIQUE(strategy_id, version)
            );
            """
            cursor.execute(create_strategy_versions_table_query)

            # Create strategy_shares table
            create_strategy_shares_table_query = """
            CREATE TABLE IF NOT EXISTS strategy_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_id INTEGER NOT NULL,
                shared_with_user_id INTEGER NOT NULL,
                permission VARCHAR(20) DEFAULT 'view',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_id) REFERENCES strategies (id) ON DELETE CASCADE,
                FOREIGN KEY (shared_with_user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(strategy_id, shared_with_user_id)
            );
            """
            cursor.execute(create_strategy_shares_table_query)

            # =========================================================================
            # BACKTEST LAYER 1: RUN - Configuration + Reproducibility
            # =========================================================================

            create_backtest_runs_table = """
            CREATE TABLE IF NOT EXISTS backtest_runs (
                backtest_id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_version_id INTEGER,
                user_id INTEGER,

                status TEXT DEFAULT 'pending',
                alias TEXT,
                description TEXT,

                strategy_name TEXT NOT NULL,
                strategy_version TEXT NOT NULL,

                start_date DATE NOT NULL,
                end_date DATE NOT NULL,

                symbols TEXT,
                timeframes TEXT,

                initial_balance REAL,
                final_balance REAL,

                commission_model TEXT,
                slippage_model TEXT,
                spread_model TEXT,

                execution_model TEXT,
                fill_model TEXT,

                risk_model TEXT,
                position_sizing_model TEXT,

                engine_type TEXT NOT NULL,
                data_resolution TEXT NOT NULL,

                config_hash TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,

                FOREIGN KEY (strategy_version_id) REFERENCES strategy_versions (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_backtest_runs_table)

            # =========================================================================
            # BACKTEST LAYER 2: FACTS - Trades, Events, Equity
            # =========================================================================

            create_backtest_trades_table = """
            CREATE TABLE IF NOT EXISTS backtest_trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id INTEGER NOT NULL,

                -- 1. Trade Identification & Attribution
                ticket INTEGER,
                symbol TEXT,
                side TEXT,
                magic_number INTEGER,
                strategy_name TEXT,

                -- 2. Strategy Context
                setup_id TEXT,
                sample_type TEXT,
                comment TEXT,

                -- 3. Trade Timing
                signal_timeframe TEXT,
                execution_timeframe TEXT,
                session TEXT,
                day_of_week INTEGER,
                hour_of_day INTEGER,

                open_time TIMESTAMP,
                close_time TIMESTAMP,
                time_in_trade_seconds REAL,
                bars_in_trade INTEGER,

                -- 4. Entry Definition
                open_price REAL,
                orig_open_price REAL,
                orig_open_time TIMESTAMP,
                requested_entry_price REAL,
                spread_at_entry REAL,
                atr_at_entry REAL,
                position_size REAL,

                -- 5. Exit Definition
                close_price REAL,
                requested_exit_price REAL,
                close_type TEXT,
                exit_reason TEXT,

                -- 6. Trade Plan & Risk
                stop_loss_price REAL,
                profit_target_price REAL,
                initial_risk_pips REAL,
                initial_risk_usd REAL,

                -- 7. Account State
                balance_at_entry REAL,
                equity_at_entry REAL,
                margin_used REAL,
                free_margin REAL,

                -- 8. Trade Management
                max_position_size REAL,
                partial_close_count INTEGER,
                trailing_stop_used BOOLEAN,
                breakeven_triggered BOOLEAN,

                -- 9. Execution Quality
                slippage_usd REAL,
                fill_price_deviation REAL,
                execution_latency_ms INTEGER,

                -- 10. Performance Results
                pnl REAL,
                pnl_pips REAL,
                commission REAL,
                swap REAL,
                r_multiple REAL,
                buy_hold REAL,
                buy_hold_pips REAL,

                -- 11. Excursion & Drawdown Analytics
                mae_usd REAL,
                mae_pips REAL,
                mfe_usd REAL,
                mfe_pips REAL,
                drawdown REAL,

                -- 12. Regime & Research Tags
                market_regime TEXT,
                volatility_bucket TEXT,
                correlation_cluster TEXT,

                -- 13. Compliance & Audit
                rule_violation BOOLEAN,
                manual_intervention BOOLEAN,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_backtest_trades_table)

            create_backtest_trade_events_table = """
            CREATE TABLE IF NOT EXISTS backtest_trade_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_id INTEGER NOT NULL,

                event_time TIMESTAMP,
                event_type TEXT,

                price REAL,
                size REAL,

                stop_loss_price REAL,
                take_profit_price REAL,

                fee REAL,
                slippage_usd REAL,

                notes TEXT,

                FOREIGN KEY (trade_id) REFERENCES backtest_trades (trade_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_backtest_trade_events_table)

            create_backtest_equity_curve_table = """
            CREATE TABLE IF NOT EXISTS backtest_equity_curve (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id INTEGER NOT NULL,

                timestamp TIMESTAMP,
                equity REAL,
                balance REAL,
                drawdown REAL,
                exposure REAL,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_backtest_equity_curve_table)

            # =========================================================================
            # BACKTEST LAYER 3: DERIVED - Finance Module Metrics
            # =========================================================================

            create_finance_trade_metrics_table = """
            CREATE TABLE IF NOT EXISTS finance_trade_metrics (
                backtest_id INTEGER PRIMARY KEY,

                total_trades INTEGER,
                winning_trades INTEGER,
                losing_trades INTEGER,

                win_rate REAL,
                loss_rate REAL,

                avg_win REAL,
                avg_loss REAL,
                largest_win REAL,
                largest_loss REAL,

                expectancy REAL,
                expectancy_r REAL,

                profit_factor REAL,
                payoff_ratio REAL,
                edge_ratio REAL,

                avg_r_multiple REAL,
                median_r_multiple REAL,
                max_r_multiple REAL,
                min_r_multiple REAL,

                max_consecutive_wins INTEGER,
                max_consecutive_losses INTEGER,

                avg_time_in_trade REAL,
                median_time_in_trade REAL,

                sqn REAL,
                trade_efficiency REAL,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_finance_trade_metrics_table)

            create_finance_return_metrics_table = """
            CREATE TABLE IF NOT EXISTS finance_return_metrics (
                backtest_id INTEGER PRIMARY KEY,

                net_profit REAL,
                gross_profit REAL,
                gross_loss REAL,

                total_return REAL,
                cagr REAL,
                annualized_return REAL,

                volatility REAL,
                annualized_volatility REAL,
                downside_volatility REAL,

                skew REAL,
                kurtosis REAL,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_finance_return_metrics_table)

            create_finance_drawdown_metrics_table = """
            CREATE TABLE IF NOT EXISTS finance_drawdown_metrics (
                backtest_id INTEGER PRIMARY KEY,

                max_drawdown REAL,
                max_drawdown_pct REAL,
                avg_drawdown REAL,

                max_drawdown_duration INTEGER,
                avg_drawdown_duration REAL,

                ulcer_index REAL,
                pain_index REAL,
                pain_ratio REAL,

                recovery_factor REAL,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_finance_drawdown_metrics_table)

            create_finance_ratio_metrics_table = """
            CREATE TABLE IF NOT EXISTS finance_ratio_metrics (
                backtest_id INTEGER PRIMARY KEY,

                sharpe REAL,
                sortino REAL,
                calmar REAL,
                omega REAL,

                information_ratio REAL,
                gain_to_pain REAL,

                profit_to_mae_ratio REAL,
                mfe_to_mae_ratio REAL,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_finance_ratio_metrics_table)

            create_finance_risk_metrics_table = """
            CREATE TABLE IF NOT EXISTS finance_risk_metrics (
                backtest_id INTEGER PRIMARY KEY,

                var_95 REAL,
                cvar_95 REAL,
                var_99 REAL,
                cvar_99 REAL,

                risk_of_ruin REAL,

                max_exposure REAL,
                avg_exposure REAL,
                exposure_time_ratio REAL,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_finance_risk_metrics_table)

            create_finance_efficiency_metrics_table = """
            CREATE TABLE IF NOT EXISTS finance_efficiency_metrics (
                backtest_id INTEGER PRIMARY KEY,

                mfe_efficiency REAL,
                mae_efficiency REAL,
                exit_efficiency REAL,

                win_efficiency REAL,
                loss_containment_efficiency REAL,

                time_efficiency REAL,
                return_per_trade REAL,
                return_per_unit_risk REAL,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_finance_efficiency_metrics_table)

            # =========================================================================
            # BACKTEST LAYER 4: RESEARCH - Benchmarks & Distributions
            # =========================================================================

            create_finance_benchmark_metrics_table = """
            CREATE TABLE IF NOT EXISTS finance_benchmark_metrics (
                backtest_id INTEGER NOT NULL,
                benchmark_name TEXT NOT NULL,

                alpha REAL,
                beta REAL,
                r_squared REAL,
                correlation REAL,
                tracking_error REAL,

                up_capture REAL,
                down_capture REAL,

                PRIMARY KEY (backtest_id, benchmark_name),
                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_finance_benchmark_metrics_table)

            create_finance_distributions_table = """
            CREATE TABLE IF NOT EXISTS finance_distributions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id INTEGER NOT NULL,

                metric_name TEXT NOT NULL,

                mean REAL,
                median REAL,
                std REAL,
                min REAL,
                max REAL,

                percentile_5 REAL,
                percentile_25 REAL,
                percentile_75 REAL,
                percentile_95 REAL,

                skewness REAL,
                kurtosis REAL,

                dist_type TEXT,
                dist_params TEXT,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_finance_distributions_table)

            # =========================================================================
            # OPTIMIZATION TABLES - Parameter Search & Walk-Forward
            # =========================================================================

            create_optimization_runs_table = """
            CREATE TABLE IF NOT EXISTS optimization_runs (
                optimization_id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                strategy_version TEXT,

                optimization_type TEXT NOT NULL,
                optimization_method TEXT NOT NULL,

                start_date DATE NOT NULL,
                end_date DATE NOT NULL,

                symbols TEXT,
                timeframes TEXT,

                parameter_space TEXT NOT NULL,

                objective_function TEXT NOT NULL,
                constraints TEXT,

                total_combinations INTEGER,
                completed_combinations INTEGER DEFAULT 0,

                best_backtest_id INTEGER,
                best_score REAL,
                best_parameters TEXT,

                n_jobs INTEGER DEFAULT 1,
                status TEXT DEFAULT 'pending',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,

                FOREIGN KEY (best_backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_optimization_runs_table)

            create_optimization_results_table = """
            CREATE TABLE IF NOT EXISTS optimization_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                optimization_id INTEGER NOT NULL,
                backtest_id INTEGER NOT NULL,

                parameters TEXT NOT NULL,

                score REAL NOT NULL,
                rank INTEGER,

                total_trades INTEGER,
                win_rate REAL,
                profit_factor REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,

                is_best BOOLEAN DEFAULT 0,
                is_top_10 BOOLEAN DEFAULT 0,

                overfitting_score REAL,
                stability_score REAL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (optimization_id) REFERENCES optimization_runs (optimization_id) ON DELETE CASCADE,
                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_optimization_results_table)

            # Walk-Forward Analysis windows
            create_walk_forward_windows_table = """
            CREATE TABLE IF NOT EXISTS walk_forward_windows (
                window_id INTEGER PRIMARY KEY AUTOINCREMENT,
                optimization_id INTEGER NOT NULL,
                window_number INTEGER NOT NULL,

                -- Window periods
                train_start DATE NOT NULL,
                train_end DATE NOT NULL,
                test_start DATE NOT NULL,
                test_end DATE NOT NULL,

                -- Best parameters from training
                best_parameters TEXT NOT NULL,

                -- Training (in-sample) performance
                train_backtest_id INTEGER,
                train_return REAL,
                train_sharpe REAL,
                train_drawdown REAL,
                train_total_trades INTEGER,

                -- Testing (out-of-sample) performance
                test_backtest_id INTEGER,
                test_return REAL,
                test_sharpe REAL,
                test_drawdown REAL,
                test_total_trades INTEGER,

                -- Overfitting metrics
                overfitting_ratio REAL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (optimization_id) REFERENCES optimization_runs (optimization_id) ON DELETE CASCADE,
                FOREIGN KEY (train_backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE SET NULL,
                FOREIGN KEY (test_backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_walk_forward_windows_table)

            # Monte Carlo simulations
            create_monte_carlo_simulations_table = """
            CREATE TABLE IF NOT EXISTS monte_carlo_simulations (
                simulation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id INTEGER NOT NULL,

                -- Configuration
                simulation_type TEXT NOT NULL,
                num_simulations INTEGER NOT NULL,
                block_size INTEGER,
                random_seed INTEGER,

                -- Summary statistics
                mean_return REAL,
                median_return REAL,
                std_return REAL,

                -- Confidence intervals
                ci_95_lower REAL,
                ci_95_upper REAL,
                ci_99_lower REAL,
                ci_99_upper REAL,

                -- Risk metrics
                probability_of_profit REAL,
                probability_of_ruin REAL,
                expected_shortfall_95 REAL,

                -- Percentiles
                percentile_5 REAL,
                percentile_25 REAL,
                percentile_50 REAL,
                percentile_75 REAL,
                percentile_95 REAL,

                -- Original metrics for comparison
                original_return REAL,
                original_sharpe REAL,
                original_max_dd REAL,

                -- Full distribution data (JSON)
                distribution_data TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_monte_carlo_simulations_table)

            # Create indices for performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_backtest_trades_backtest_id ON backtest_trades(backtest_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_backtest_trades_open_time ON backtest_trades(open_time)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_backtest_equity_backtest_id ON backtest_equity_curve(backtest_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trade_events_trade_id ON backtest_trade_events(trade_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_optimization_results_optimization_id ON optimization_results(optimization_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_optimization_results_score ON optimization_results(score DESC)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_walk_forward_windows_optimization_id ON walk_forward_windows(optimization_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_monte_carlo_simulations_backtest_id ON monte_carlo_simulations(backtest_id)"
            )

            # =========================================================================
            # LIVE TRADING TABLES
            # =========================================================================

            # Live trading sessions
            create_live_trading_sessions_table = """
            CREATE TABLE IF NOT EXISTS live_trading_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_name TEXT,

                -- Session configuration
                status TEXT DEFAULT 'stopped',
                mode TEXT DEFAULT 'paper',

                -- Portfolio settings
                max_total_risk_pct REAL DEFAULT 2.0,
                max_positions INTEGER DEFAULT 5,
                max_correlation REAL DEFAULT 0.7,
                max_drawdown_pct REAL DEFAULT 10.0,

                -- Timing
                trading_hours_start TEXT,
                trading_hours_end TEXT,
                allowed_days TEXT,

                -- State tracking
                started_at TIMESTAMP,
                stopped_at TIMESTAMP,
                last_heartbeat TIMESTAMP,
                error_message TEXT,

                -- Statistics
                total_signals_detected INTEGER DEFAULT 0,
                total_signals_executed INTEGER DEFAULT 0,
                total_signals_rejected INTEGER DEFAULT 0,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_live_trading_sessions_table)

            # Session strategies (many-to-many)
            create_session_strategies_table = """
            CREATE TABLE IF NOT EXISTS session_strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                strategy_version_id INTEGER NOT NULL,

                -- Strategy configuration
                is_active BOOLEAN DEFAULT 1,
                symbols TEXT NOT NULL,
                timeframes TEXT NOT NULL,

                -- Risk per strategy
                max_risk_per_trade_pct REAL DEFAULT 1.0,
                position_size_type TEXT DEFAULT 'risk',
                position_size_value REAL DEFAULT 1.0,

                -- Parameters override
                strategy_params TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (session_id) REFERENCES live_trading_sessions (session_id) ON DELETE CASCADE,
                FOREIGN KEY (strategy_version_id) REFERENCES strategy_versions (id) ON DELETE CASCADE,
                UNIQUE(session_id, strategy_version_id)
            );
            """
            cursor.execute(create_session_strategies_table)

            # Detected signals
            create_live_signals_table = """
            CREATE TABLE IF NOT EXISTS live_signals (
                signal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                strategy_version_id INTEGER NOT NULL,

                -- Signal details
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                signal_time TIMESTAMP NOT NULL,

                -- Entry details
                entry_price REAL,
                stop_loss REAL,
                take_profit REAL,

                -- Risk calculation
                risk_pips REAL,
                risk_usd REAL,
                position_size REAL,
                reward_risk_ratio REAL,

                -- Signal metadata
                signal_reason TEXT,
                signal_data TEXT,

                -- Processing status
                status TEXT DEFAULT 'pending',
                rejection_reason TEXT,

                -- Execution reference
                position_id INTEGER,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,

                FOREIGN KEY (session_id) REFERENCES live_trading_sessions (session_id) ON DELETE CASCADE,
                FOREIGN KEY (strategy_version_id) REFERENCES strategy_versions (id) ON DELETE SET NULL,
                FOREIGN KEY (position_id) REFERENCES live_positions (position_id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_live_signals_table)

            # Live positions (active trades)
            create_live_positions_table = """
            CREATE TABLE IF NOT EXISTS live_positions (
                position_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                signal_id INTEGER,

                -- MT5 details
                mt5_ticket INTEGER UNIQUE,
                mt5_order INTEGER,

                -- Position details
                symbol TEXT NOT NULL,
                type TEXT NOT NULL,

                -- Entry
                open_time TIMESTAMP NOT NULL,
                open_price REAL NOT NULL,
                position_size REAL NOT NULL,

                -- Current state
                current_price REAL,
                current_profit REAL,
                current_profit_pct REAL,

                -- Risk management
                initial_stop_loss REAL,
                current_stop_loss REAL,
                initial_take_profit REAL,
                current_take_profit REAL,

                -- Trade management flags
                breakeven_activated BOOLEAN DEFAULT 0,
                trailing_stop_activated BOOLEAN DEFAULT 0,
                partial_close_count INTEGER DEFAULT 0,

                -- Status
                status TEXT DEFAULT 'open',
                close_reason TEXT,

                -- Exit
                close_time TIMESTAMP,
                close_price REAL,
                final_profit REAL,
                final_profit_pct REAL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (session_id) REFERENCES live_trading_sessions (session_id) ON DELETE CASCADE,
                FOREIGN KEY (signal_id) REFERENCES live_signals (signal_id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_live_positions_table)

            # Position events (audit trail)
            create_live_position_events_table = """
            CREATE TABLE IF NOT EXISTS live_position_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL,

                event_type TEXT NOT NULL,
                event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                -- Event details
                price REAL,
                size REAL,
                stop_loss REAL,
                take_profit REAL,

                profit REAL,
                reason TEXT,
                metadata TEXT,

                FOREIGN KEY (position_id) REFERENCES live_positions (position_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_live_position_events_table)

            # =========================================================================
            # DATA MANAGEMENT TABLES
            # =========================================================================

            create_market_data_table = """
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                source TEXT NOT NULL,

                start_date TIMESTAMP,
                end_date TIMESTAMP,
                record_count INTEGER,

                validation_report TEXT,  -- JSON string
                file_path TEXT NOT NULL,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_market_data_table)

            # Risk management rules
            create_live_risk_rules_table = """
            CREATE TABLE IF NOT EXISTS live_risk_rules (
                rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,

                rule_name TEXT NOT NULL,
                rule_type TEXT NOT NULL,

                -- Rule configuration (JSON)
                rule_config TEXT NOT NULL,

                is_active BOOLEAN DEFAULT 1,
                violation_action TEXT DEFAULT 'reject',

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (session_id) REFERENCES live_trading_sessions (session_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_live_risk_rules_table)

            # Session logs
            create_live_session_logs_table = """
            CREATE TABLE IF NOT EXISTS live_session_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,

                log_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                log_level TEXT NOT NULL,
                log_category TEXT NOT NULL,

                message TEXT NOT NULL,
                details TEXT,

                FOREIGN KEY (session_id) REFERENCES live_trading_sessions (session_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_live_session_logs_table)

            # Indices for live trading performance
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_sessions_user ON live_trading_sessions(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_sessions_status ON live_trading_sessions(status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_signals_session ON live_signals(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_signals_time ON live_signals(signal_time)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_positions_session ON live_positions(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_positions_status ON live_positions(status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_positions_mt5_ticket ON live_positions(mt5_ticket)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_logs_session ON live_session_logs(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_live_logs_time ON live_session_logs(log_time)"
            )

            conn.commit()
            logger.info(
                "Database schema initialized successfully with 4-layer architecture + optimization + live trading"
            )
            logger.info("  Layer 1 (Run): backtest_runs")
            logger.info(
                "  Layer 2 (Facts): backtest_trades, backtest_trade_events, backtest_equity_curve"
            )
            logger.info("  Layer 3 (Derived): finance_*_metrics tables")
            logger.info(
                "  Layer 4 (Research): finance_benchmark_metrics, finance_distributions"
            )
            logger.info("  Optimization: optimization_runs, optimization_results")
            logger.info(
                "  Live Trading: live_trading_sessions, session_strategies, live_signals, live_positions, etc."
            )
            return True

        except sqlite3.Error as e:
            logger.error(f"An error occurred during database creation: {e}")
            return False
        finally:
            if conn:
                conn.close()
                logger.info("Database connection closed.")

    def delete_database(self) -> bool:
        """
        Delete the database file.

        Useful for testing or resetting the environment.
        """
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
                logger.info(f"Database deleted at: {self.db_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete database: {e}")
                return False
        else:
            logger.warning(f"Database file not found at: {self.db_path}")
            return False
