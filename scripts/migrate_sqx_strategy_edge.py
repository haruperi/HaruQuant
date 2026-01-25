"""Migrate sqx_strategy_edge to single-row strategy_name schema."""

import os
import sqlite3

DB_PATH = "d:/Trading/Applications/HaruQuant/data/database/haruquant.db"


def migrate() -> None:
    """Run SQX strategy edge migration."""
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Starting migration of sqx_strategy_edge (data will be cleared)...")

        cursor.execute("ALTER TABLE sqx_strategy_edge RENAME TO sqx_strategy_edge_old")

        create_new_table_query = """
        CREATE TABLE sqx_strategy_edge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Identity
            symbol TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            timeframe TEXT,
            source_symbol TEXT,
            source_timeframe TEXT,
            stage TEXT,
            last_seen_at TEXT,
            last_import_name TEXT,

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

            drawdown REAL,
            actual_drawdown REAL,
            actual_drawdown_over_maxdd REAL,
            avg_drawdown REAL,
            avg_drawdown_pct REAL,
            ulcer_index_pct REAL,
            ulcer_performance_index REAL,

            win_percent REAL,
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

            mc_survival_rate REAL,
            mc_retdd_p95_ratio REAL,
            mc_dd_inflation REAL,
            mc_overall_survival_rate REAL,
            mc_overall_retdd_ratio REAL,

            param_perturb_profitable_rate REAL,
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
            rejected INTEGER DEFAULT 0,

            -- Audit / bookkeeping
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),

            UNIQUE(strategy_name)
        );
        """
        cursor.execute(create_new_table_query)

        cursor.execute("DROP TABLE sqx_strategy_edge_old")

        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_sqx_strategies_symbol ON sqx_strategy_edge(symbol)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_sqx_strategies_score ON sqx_strategy_edge(symbol, final_score DESC)"
        )

        conn.commit()
        print("Migration completed successfully (table cleared).")

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
