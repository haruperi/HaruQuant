"""Database schema management module."""

import os
import sqlite3

from backend.common.logger import logger


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

            # =========================================================================
            # EDGE DISCOVERY TABLES
            # =========================================================================

            create_edge_discovery_runs_table = """
            CREATE TABLE IF NOT EXISTS edge_discovery_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,

                -- Symbol and timeframe
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,

                -- EDS type
                eds_name TEXT NOT NULL,
                eds_type TEXT NOT NULL,

                -- Configuration (JSON)
                config TEXT NOT NULL,

                -- Data range
                start_pos INTEGER,
                end_pos INTEGER,
                bar_count INTEGER,

                -- Results summary
                n_trades INTEGER,
                expectancy_r REAL,
                win_rate REAL,
                profit_factor REAL,

                -- Statistical validation
                ci_low REAL,
                ci_high REAL,
                p_value_perm REAL,

                -- Verdict
                verdict TEXT,
                edge_confirmed BOOLEAN DEFAULT 0,

                -- Bootstrap/Permutation config
                n_boot INTEGER,
                n_perm INTEGER,
                block_size INTEGER,
                ci_level REAL,

                -- Extras (JSON for additional stats)
                extras TEXT,

                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_edge_discovery_runs_table)

            create_edge_discovery_trades_table = """
            CREATE TABLE IF NOT EXISTS edge_discovery_trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,

                -- Trade timing
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,

                -- Trade details
                side TEXT,
                entry_price REAL,
                exit_price REAL,

                -- R-multiple metrics
                r_multiple REAL,
                mae_r REAL,
                mfe_r REAL,

                -- Holding period
                hold_bars INTEGER,

                -- Metadata (JSON)
                meta TEXT,

                FOREIGN KEY (run_id) REFERENCES edge_discovery_runs (run_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_discovery_trades_table)

            create_edge_discovery_stats_table = """
            CREATE TABLE IF NOT EXISTS edge_discovery_stats (
                run_id INTEGER PRIMARY KEY,

                -- Core metrics
                n_trades INTEGER,
                expectancy_r REAL,
                win_rate REAL,
                profit_factor REAL,

                -- Excursion metrics
                median_mae_r REAL,
                median_mfe_r REAL,
                avg_hold_bars REAL,

                -- Statistical validation
                ci_low REAL,
                ci_high REAL,
                p_value_perm REAL,

                -- Additional metrics (JSON)
                extras TEXT,

                FOREIGN KEY (run_id) REFERENCES edge_discovery_runs (run_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_discovery_stats_table)

            # Edge discovery indices
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_runs_symbol ON edge_discovery_runs(symbol)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_runs_eds_type ON edge_discovery_runs(eds_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_runs_verdict ON edge_discovery_runs(verdict)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_trades_run_id ON edge_discovery_trades(run_id)"
            )

            create_edge_core_metric_runs_table = """
            CREATE TABLE IF NOT EXISTS edge_core_metric_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                data_source TEXT NOT NULL,
                range_by TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                number_of_bars INTEGER,
                bar_count INTEGER,
                is_valid BOOLEAN DEFAULT 1,
                warning_count INTEGER DEFAULT 0,
                fatal_error_count INTEGER DEFAULT 0,
                report TEXT,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_edge_core_metric_runs_table)

            create_edge_core_metric_values_table = """
            CREATE TABLE IF NOT EXISTS edge_core_metric_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                family TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                value_num REAL,
                value_text TEXT,
                value_type TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES edge_core_metric_runs (run_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_core_metric_values_table)

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_core_runs_symbol ON edge_core_metric_runs(symbol)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_core_runs_created_at ON edge_core_metric_runs(created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_core_values_run_id ON edge_core_metric_values(run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_core_values_family_key ON edge_core_metric_values(family, metric_key)"
            )

            create_edge_market_structure_runs_table = """
            CREATE TABLE IF NOT EXISTS edge_market_structure_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                data_source TEXT NOT NULL,
                range_by TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                number_of_bars INTEGER,
                bar_count INTEGER,
                is_valid BOOLEAN DEFAULT 1,
                warning_count INTEGER DEFAULT 0,
                fatal_error_count INTEGER DEFAULT 0,
                report TEXT,
                summary TEXT,
                calibration_metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_edge_market_structure_runs_table)
            cursor.execute("PRAGMA table_info(edge_market_structure_runs)")
            market_structure_run_columns = {row[1] for row in cursor.fetchall()}
            if "calibration_metadata" not in market_structure_run_columns:
                cursor.execute(
                    "ALTER TABLE edge_market_structure_runs ADD COLUMN calibration_metadata TEXT"
                )

            create_edge_market_structure_values_table = """
            CREATE TABLE IF NOT EXISTS edge_market_structure_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                family TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                value_num REAL,
                value_text TEXT,
                value_type TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES edge_market_structure_runs (run_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_market_structure_values_table)

            create_edge_market_structure_scores_table = """
            CREATE TABLE IF NOT EXISTS edge_market_structure_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                score_group TEXT,
                score_key TEXT NOT NULL,
                label TEXT NOT NULL,
                raw_value TEXT,
                score REAL,
                weight REAL,
                contribution REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES edge_market_structure_runs (run_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_market_structure_scores_table)
            cursor.execute("PRAGMA table_info(edge_market_structure_scores)")
            market_structure_score_columns = {row[1] for row in cursor.fetchall()}
            if "score_group" not in market_structure_score_columns:
                cursor.execute(
                    "ALTER TABLE edge_market_structure_scores ADD COLUMN score_group TEXT"
                )

            create_edge_market_structure_swings_table = """
            CREATE TABLE IF NOT EXISTS edge_market_structure_swings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                swing_type TEXT NOT NULL,
                label TEXT NOT NULL,
                swing_index INTEGER NOT NULL,
                atr_value REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES edge_market_structure_runs (run_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_market_structure_swings_table)

            create_edge_market_structure_legs_table = """
            CREATE TABLE IF NOT EXISTS edge_market_structure_legs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                direction TEXT NOT NULL,
                amplitude_pips REAL,
                duration_bars INTEGER,
                efficiency_ratio REAL,
                directional_consistency REAL,
                pullback_depth REAL,
                pullback_duration INTEGER,
                continuation_after_pullback BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES edge_market_structure_runs (run_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_market_structure_legs_table)

            create_edge_market_structure_evaluations_table = """
            CREATE TABLE IF NOT EXISTS edge_market_structure_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                run_created_at TEXT,
                predicted_verdict TEXT,
                realized_verdict TEXT,
                matched BOOLEAN,
                decision_confidence_score REAL,
                confidence_bucket TEXT,
                forward_end TEXT,
                net_move_pips REAL,
                path_pips REAL,
                efficiency REAL,
                reversion_ratio REAL,
                flip_rate REAL,
                avg_range_pips REAL,
                max_excursion_pips REAL,
                continuation_label TEXT,
                range_reentry_label TEXT,
                breakout_failure_label TEXT,
                chop_label TEXT,
                calibration_metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES edge_market_structure_runs (run_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_market_structure_evaluations_table)

            create_edge_profile_snapshots_table = """
            CREATE TABLE IF NOT EXISTS edge_profile_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                data_source TEXT,
                range_by TEXT,
                model_version TEXT,
                baseline_id TEXT,
                core_metric_run_id INTEGER,
                market_structure_run_id INTEGER,
                dataset_meta TEXT,
                core_metric_summary TEXT,
                seasonality_summary TEXT,
                market_structure_summary TEXT,
                scorecard_summary TEXT,
                automation_metadata TEXT,
                artifact_refs TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL,
                FOREIGN KEY (core_metric_run_id) REFERENCES edge_core_metric_runs (run_id) ON DELETE SET NULL,
                FOREIGN KEY (market_structure_run_id) REFERENCES edge_market_structure_runs (run_id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_edge_profile_snapshots_table)
            try:
                cursor.execute(
                    "ALTER TABLE edge_profile_snapshots ADD COLUMN automation_metadata TEXT"
                )
            except Exception:
                pass

            create_edge_profile_snapshot_metrics_table = """
            CREATE TABLE IF NOT EXISTS edge_profile_snapshot_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                section TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                value_num REAL,
                value_text TEXT,
                value_type TEXT NOT NULL,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snapshot_id) REFERENCES edge_profile_snapshots (snapshot_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_profile_snapshot_metrics_table)

            create_edge_profile_snapshot_scores_table = """
            CREATE TABLE IF NOT EXISTS edge_profile_snapshot_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                score_key TEXT NOT NULL,
                label TEXT NOT NULL,
                score REAL,
                confidence TEXT,
                explanation TEXT,
                inputs TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snapshot_id) REFERENCES edge_profile_snapshots (snapshot_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_profile_snapshot_scores_table)

            create_edge_profile_snapshot_strategy_fit_table = """
            CREATE TABLE IF NOT EXISTS edge_profile_snapshot_strategy_fit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                rank_order INTEGER NOT NULL,
                archetype TEXT NOT NULL,
                fit_score REAL,
                rationale TEXT,
                warnings TEXT,
                anti_fit_conditions TEXT,
                inputs TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snapshot_id) REFERENCES edge_profile_snapshots (snapshot_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_profile_snapshot_strategy_fit_table)

            create_edge_profile_snapshot_artifacts_table = """
            CREATE TABLE IF NOT EXISTS edge_profile_snapshot_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                artifact_type TEXT NOT NULL,
                artifact_ref TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (snapshot_id) REFERENCES edge_profile_snapshots (snapshot_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_edge_profile_snapshot_artifacts_table)

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_market_runs_symbol ON edge_market_structure_runs(symbol)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_market_runs_created_at ON edge_market_structure_runs(created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_market_values_run_id ON edge_market_structure_values(run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_market_scores_run_id ON edge_market_structure_scores(run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_market_swings_run_id ON edge_market_structure_swings(run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_market_evals_run_id ON edge_market_structure_evaluations(run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_market_evals_symbol_timeframe ON edge_market_structure_evaluations(symbol, timeframe)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_market_legs_run_id ON edge_market_structure_legs(run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_profile_snapshots_symbol_timeframe ON edge_profile_snapshots(symbol, timeframe)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_profile_snapshots_created_at ON edge_profile_snapshots(created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_profile_snapshot_metrics_snapshot_id ON edge_profile_snapshot_metrics(snapshot_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_profile_snapshot_metrics_section_key ON edge_profile_snapshot_metrics(section, metric_key)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_profile_snapshot_scores_snapshot_id ON edge_profile_snapshot_scores(snapshot_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_profile_snapshot_strategy_fit_snapshot_id ON edge_profile_snapshot_strategy_fit(snapshot_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_edge_profile_snapshot_artifacts_snapshot_id ON edge_profile_snapshot_artifacts(snapshot_id)"
            )

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
                stop_mode TEXT DEFAULT 'manual',
                stop_at TIMESTAMP,

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
            cursor.execute("PRAGMA table_info(live_trading_sessions)")
            live_session_columns = {row[1] for row in cursor.fetchall()}
            if "stop_mode" not in live_session_columns:
                cursor.execute(
                    "ALTER TABLE live_trading_sessions ADD COLUMN stop_mode TEXT DEFAULT 'manual'"
                )
            if "stop_at" not in live_session_columns:
                cursor.execute(
                    "ALTER TABLE live_trading_sessions ADD COLUMN stop_at TIMESTAMP"
                )

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
                FOREIGN KEY (strategy_version_id) REFERENCES strategy_versions (id) ON DELETE CASCADE
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

            # =========================================================================
            # SIMULATOR TABLES
            # =========================================================================

            create_simulator_deals_table = """
            CREATE TABLE IF NOT EXISTS simulator_deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT,
                magic INTEGER,
                symbol TEXT,
                type TEXT,
                direction TEXT,
                volume REAL,
                price REAL,
                spread REAL,
                sl REAL,
                tp REAL,
                commission REAL,
                margin_required REAL,
                fee REAL,
                swap REAL,
                profit REAL,
                comment TEXT,
                reason TEXT,
                entry_reason TEXT,
                session_id TEXT
            );
            """
            cursor.execute(create_simulator_deals_table)

            cursor.execute("PRAGMA table_info(simulator_deals)")
            simulator_columns = {row[1] for row in cursor.fetchall()}
            if "spread" not in simulator_columns:
                cursor.execute("ALTER TABLE simulator_deals ADD COLUMN spread REAL")
            if "entry_reason" not in simulator_columns:
                cursor.execute(
                    "ALTER TABLE simulator_deals ADD COLUMN entry_reason TEXT"
                )
            if "session_id" not in simulator_columns:
                cursor.execute("ALTER TABLE simulator_deals ADD COLUMN session_id TEXT")

            # Simulation sessions (new simulator flow)
            create_simulation_sessions_table = """
            CREATE TABLE IF NOT EXISTS simulation_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_name TEXT,
                mode TEXT NOT NULL DEFAULT 'manual',
                status TEXT NOT NULL DEFAULT 'running',
                symbol TEXT,
                timeframe TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                initial_balance REAL,
                speed_multiplier REAL DEFAULT 1.0,
                current_bar_index INTEGER DEFAULT 0,
                total_bars INTEGER,
                replay_source TEXT,
                replay_backtest_id INTEGER,
                replay_file_name TEXT,
                config TEXT,
                runtime_owner TEXT,
                lease_expires_at TIMESTAMP,
                last_heartbeat_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_simulation_sessions_table)

            cursor.execute("PRAGMA table_info(simulation_sessions)")
            simulation_session_columns = {row[1] for row in cursor.fetchall()}
            if "runtime_owner" not in simulation_session_columns:
                cursor.execute(
                    "ALTER TABLE simulation_sessions ADD COLUMN runtime_owner TEXT"
                )
            if "lease_expires_at" not in simulation_session_columns:
                cursor.execute(
                    "ALTER TABLE simulation_sessions ADD COLUMN lease_expires_at TIMESTAMP"
                )
            if "last_heartbeat_at" not in simulation_session_columns:
                cursor.execute(
                    "ALTER TABLE simulation_sessions ADD COLUMN last_heartbeat_at TIMESTAMP"
                )

            create_simulation_trades_table = """
            CREATE TABLE IF NOT EXISTS simulation_trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                time TIMESTAMP,
                symbol TEXT,
                side TEXT,
                price REAL,
                volume REAL,
                sl REAL,
                tp REAL,
                pnl REAL,
                reason TEXT,
                source TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES simulation_sessions (session_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_simulation_trades_table)

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_simulation_sessions_user ON simulation_sessions(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_simulation_sessions_status ON simulation_sessions(status)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_simulation_sessions_created ON simulation_sessions(created_at)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_simulation_trades_session ON simulation_trades(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_simulation_trades_time ON simulation_trades(time)"
            )

            # =========================================================================
            # SQX STRATEGY MASTER TABLES
            # =========================================================================

            # Strategies master table (SQX)
            create_sqx_strategy_edge_table = """
            CREATE TABLE IF NOT EXISTS sqx_strategy_edge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                -- Identity
                symbol TEXT NOT NULL,                 -- canonical, e.g. 'EURUSD'
                strategy_name TEXT NOT NULL,          -- from SQX 'Strategy Name'
                timeframe TEXT,                       -- e.g. 'M1,M5,H1'
                source_symbol TEXT,                   -- raw SQX symbol (e.g. 'EURUSD_dukascopy')
                source_timeframe TEXT,                -- raw SQX timeframe field if different
                stage TEXT,                           -- last stage seen (e.g., 'CORE','SPREAD_P99','MC_OVERALL','WFM'...)
                last_seen_at TEXT,                    -- ISO timestamp
                last_import_name TEXT,                -- import label / filename

                -- Baseline / databank metrics (commonly exported)
                fitness_is REAL,
                net_profit REAL,
                trades INTEGER,
                profit_factor REAL,
                annual_return_pct REAL,
                max_drawdown_pct REAL,
                cagr REAL,
                cagr_max_dd_pct REAL,
                ret_dd_ratio REAL,
                calmar_ratio REAL,
                sharpe_ratio REAL,
                standard_dev REAL,

                drawdown REAL,                        -- raw DD value (units depend on SQX settings)
                actual_drawdown REAL,
                actual_drawdown_over_maxdd REAL,
                avg_drawdown REAL,
                avg_drawdown_pct REAL,
                ulcer_index_pct REAL,
                ulcer_performance_index REAL,

                win_percent REAL,                     -- 0..1 preferred (store 0..1)
                win_loss_ratio REAL,
                ts_index REAL,
                ts_win_loss_ratio REAL,
                zscore REAL,
                zprobability REAL,
                worst_year_profit REAL,

                avg_trade REAL,
                avg_abs_trade REAL,
                avg_trade_stddev_ratio REAL,
                avg_win REAL,
                avg_loss REAL,
                avg_consec_wins REAL,
                avg_consec_losses REAL,

                avg_bars_win REAL,
                avg_bars_loss REAL,
                avg_bars_in_trade REAL,

                stability REAL,
                symmetry REAL,
                trades_symmetry REAL,
                stagnation REAL,
                stagnation_pct REAL,

                exposure REAL,

                -- Stage-specific metrics (A1/A2/E1)
                a1_profit_factor REAL,
                a1_ret_dd_ratio REAL,
                a1_annual_return_pct REAL,
                a1_trades INTEGER,
                a1_net_profit REAL,
                a1_max_drawdown_pct REAL,
                a1_edge_score REAL,

                a2_profit_factor REAL,
                a2_ret_dd_ratio REAL,
                a2_annual_return_pct REAL,
                a2_trades INTEGER,
                a2_net_profit REAL,
                a2_max_drawdown_pct REAL,
                a2_edge_score REAL,

                e1_profit_factor REAL,
                e1_ret_dd_ratio REAL,
                e1_annual_return_pct REAL,
                e1_trades INTEGER,
                e1_net_profit REAL,
                e1_max_drawdown_pct REAL,
                e1_edge_score REAL,

                -- Stress / robustness ratios (baseline-relative). Nullable until computed/imported.
                spread_p99_retdd_ratio REAL,
                spread_max_retdd_ratio REAL,
                slip_retdd_ratio REAL,
                delay_pf_ratio REAL,

                mc_survival_rate REAL,                -- 0..1
                mc_retdd_p95_ratio REAL,
                mc_dd_inflation REAL,
                mc_overall_survival_rate REAL,         -- 0..1
                mc_overall_retdd_ratio REAL,

                param_perturb_profitable_rate REAL,    -- 0..1
                history_perturb_pf_ratio REAL,

                -- MAE/MFE trade-shape metrics (optional)
                mfe_mae_eff_median REAL,
                loss_p95_mae_r REAL,
                mfe_top1_share REAL,

                -- Deployability (optional)
                parameter_count INTEGER,
                indicator_count INTEGER,
                mtf_count INTEGER,

                -- Score outputs
                edge_score REAL,
                robust_score REAL,
                stability_score REAL,
                risk_score REAL,
                simple_score REAL,
                fragility_penalty REAL,
                base_score_0_1 REAL,
                final_score REAL,
                rank_in_symbol INTEGER,
                rejected INTEGER DEFAULT 0,            -- 0/1

                -- Audit / bookkeeping
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),

                UNIQUE(strategy_name)
            );
            """
            cursor.execute(create_sqx_strategy_edge_table)

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sqx_strategies_symbol ON sqx_strategy_edge(symbol)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sqx_strategies_score ON sqx_strategy_edge(symbol, final_score DESC)"
            )

            # Imports history
            create_imports_table = """
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_name TEXT NOT NULL,
                stage TEXT,
                imported_at TEXT DEFAULT (datetime('now')),
                row_count INTEGER,
                notes TEXT
            );
            """
            cursor.execute(create_imports_table)

            # =========================================================================
            # RISK STORAGE TABLES
            # =========================================================================

            create_risk_runs_table = """
            CREATE TABLE IF NOT EXISTS risk_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                backtest_id INTEGER,
                label TEXT,
                description TEXT,
                source TEXT DEFAULT 'manual',
                context_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_risk_runs_table)

            create_risk_snapshots_table = """
            CREATE TABLE IF NOT EXISTS risk_snapshots (
                snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                backtest_id INTEGER,
                as_of TIMESTAMP,
                summary_json TEXT DEFAULT '{}',
                governance_state_json TEXT,
                regime_state_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES risk_runs (run_id) ON DELETE CASCADE,
                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE SET NULL
            );
            """
            cursor.execute(create_risk_snapshots_table)

            create_risk_metric_rows_table = """
            CREATE TABLE IF NOT EXISTS risk_metric_rows (
                metric_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                family TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                scope TEXT NOT NULL,
                scope_key TEXT,
                numeric_value REAL,
                text_value TEXT,
                unit TEXT,
                context_json TEXT DEFAULT '{}',
                FOREIGN KEY (snapshot_id) REFERENCES risk_snapshots (snapshot_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_risk_metric_rows_table)

            create_risk_score_rows_table = """
            CREATE TABLE IF NOT EXISTS risk_score_rows (
                score_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                family TEXT NOT NULL,
                score_key TEXT NOT NULL,
                score_value REAL NOT NULL,
                confidence REAL DEFAULT 0.0,
                confidence_label TEXT DEFAULT 'low',
                explanation TEXT DEFAULT '',
                context_json TEXT DEFAULT '{}',
                FOREIGN KEY (snapshot_id) REFERENCES risk_snapshots (snapshot_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_risk_score_rows_table)

            create_risk_policy_events_table = """
            CREATE TABLE IF NOT EXISTS risk_policy_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                rule_key TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                observed_value REAL,
                threshold_value REAL,
                unit TEXT,
                scope TEXT DEFAULT 'portfolio',
                scope_key TEXT,
                context_json TEXT DEFAULT '{}',
                FOREIGN KEY (snapshot_id) REFERENCES risk_snapshots (snapshot_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_risk_policy_events_table)

            create_risk_recommendations_table = """
            CREATE TABLE IF NOT EXISTS risk_recommendations (
                recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                symbol TEXT NOT NULL,
                delta_lots REAL NOT NULL,
                current_lots REAL NOT NULL,
                projected_lots REAL NOT NULL,
                usefulness_score REAL NOT NULL,
                score_delta REAL,
                var_delta REAL,
                es_delta REAL,
                worst_scenario_loss_delta REAL,
                margin_used_delta REAL,
                governance_feasible BOOLEAN DEFAULT 0,
                explanation TEXT DEFAULT '',
                context_json TEXT DEFAULT '{}',
                FOREIGN KEY (snapshot_id) REFERENCES risk_snapshots (snapshot_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_risk_recommendations_table)

            create_risk_replay_frames_table = """
            CREATE TABLE IF NOT EXISTS risk_replay_frames (
                replay_frame_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                backtest_id INTEGER,
                frame_index INTEGER NOT NULL,
                frame_timestamp TIMESTAMP,
                capture_timestamp TIMESTAMP,
                snapshot_id INTEGER,
                score_summary_json TEXT DEFAULT '{}',
                cockpit_payload_json TEXT,
                what_if_summary_json TEXT,
                context_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES risk_runs (run_id) ON DELETE CASCADE,
                FOREIGN KEY (backtest_id) REFERENCES backtest_runs (backtest_id) ON DELETE SET NULL,
                FOREIGN KEY (snapshot_id) REFERENCES risk_snapshots (snapshot_id) ON DELETE SET NULL,
                UNIQUE(run_id, frame_index)
            );
            """
            cursor.execute(create_risk_replay_frames_table)

            create_risk_scenarios_table = """
            CREATE TABLE IF NOT EXISTS risk_scenarios (
                scenario_id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id INTEGER NOT NULL,
                scenario_name TEXT NOT NULL,
                loss REAL NOT NULL,
                stressed_var REAL,
                stressed_es REAL,
                context_json TEXT DEFAULT '{}',
                FOREIGN KEY (snapshot_id) REFERENCES risk_snapshots (snapshot_id) ON DELETE CASCADE
            );
            """
            cursor.execute(create_risk_scenarios_table)

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_runs_backtest ON risk_runs(backtest_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_snapshots_run ON risk_snapshots(run_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_snapshots_backtest ON risk_snapshots(backtest_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_metric_rows_snapshot ON risk_metric_rows(snapshot_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_score_rows_snapshot ON risk_score_rows(snapshot_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_policy_events_snapshot ON risk_policy_events(snapshot_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_recommendations_snapshot ON risk_recommendations(snapshot_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_replay_frames_run ON risk_replay_frames(run_id, frame_index)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_risk_scenarios_snapshot ON risk_scenarios(snapshot_id)"
            )

            conn.commit()
            logger.info(
                "Database schema initialized successfully with 4-layer architecture + optimization + live trading + edge discovery + risk storage"
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
                "  Edge Discovery: edge_discovery_runs, edge_discovery_trades, edge_discovery_stats"
            )
            logger.info(
                "  Live Trading: live_trading_sessions, session_strategies, live_signals, live_positions, etc."
            )
            logger.info("  SQX Strategy Edge: sqx_strategy_edge, imports")
            logger.info(
                "  Risk Storage: risk_runs, risk_snapshots, risk_metric_rows, risk_score_rows, risk_policy_events, risk_recommendations, risk_replay_frames, risk_scenarios"
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

