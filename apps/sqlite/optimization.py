"""Optimization management module."""

import contextlib
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from apps.logger import logger


class OptimizationManager:
    """
    Optimization management.

    Handles creation, storage, and retrieval of optimization runs and results.
    """

    db_path: str

    # -----------------------------------------------------------------------------------------
    # Optimization Runs
    # -----------------------------------------------------------------------------------------

    def create_optimization_run(
        self,
        strategy_name: str,
        strategy_version: str,
        optimization_type: str,
        optimization_method: str,
        start_date: datetime,
        end_date: datetime,
        parameter_space: Dict[str, Any],
        objective_function: str,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        total_combinations: Optional[int] = None,
        n_jobs: int = 1,
        status: str = "pending",
    ) -> int:
        """Create a new optimization run record."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Serialize JSON fields
            symbols_json = json.dumps(symbols) if symbols else None
            timeframes_json = json.dumps(timeframes) if timeframes else None
            parameter_space_json = json.dumps(parameter_space)
            constraints_json = json.dumps(constraints) if constraints else None

            query = """
            INSERT INTO optimization_runs (
                strategy_name, strategy_version, optimization_type, optimization_method,
                start_date, end_date, symbols, timeframes,
                parameter_space, objective_function, constraints,
                total_combinations, n_jobs, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(
                query,
                (
                    strategy_name,
                    strategy_version,
                    optimization_type,
                    optimization_method,
                    start_date,
                    end_date,
                    symbols_json,
                    timeframes_json,
                    parameter_space_json,
                    objective_function,
                    constraints_json,
                    total_combinations,
                    n_jobs,
                    status,
                ),
            )

            optimization_id = cursor.lastrowid
            if optimization_id is None:
                raise ValueError("Failed to retrieve optimization ID after insertion.")

            conn.commit()

            logger.info(f"Optimization run created with ID {optimization_id}")
            return int(optimization_id)

        except Exception as e:
            logger.error(f"Error creating optimization run: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def update_optimization_status(
        self,
        optimization_id: int,
        status: str,
        completed_combinations: Optional[int] = None,
        best_backtest_id: Optional[int] = None,
        best_score: Optional[float] = None,
        best_parameters: Optional[Dict[str, Any]] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        """Update the status and progress of an optimization run."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            update_parts = ["status = ?"]
            params: List[Any] = [status]

            if completed_combinations is not None:
                update_parts.append("completed_combinations = ?")
                params.append(completed_combinations)

            if best_backtest_id is not None:
                update_parts.append("best_backtest_id = ?")
                params.append(best_backtest_id)

            if best_score is not None:
                update_parts.append("best_score = ?")
                params.append(best_score)

            if best_parameters is not None:
                update_parts.append("best_parameters = ?")
                params.append(json.dumps(best_parameters))

            if completed_at:
                update_parts.append("completed_at = ?")
                params.append(completed_at)
            elif status in ["completed", "failed", "stopped"] and not completed_at:
                # Auto set completed_at if finishing and not provided
                update_parts.append("completed_at = CURRENT_TIMESTAMP")

            params.append(optimization_id)

            query = f"UPDATE optimization_runs SET {', '.join(update_parts)} WHERE optimization_id = ?"

            cursor.execute(query, params)
            conn.commit()

            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error updating optimization status: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def get_optimization_run(self, optimization_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve an optimization run by ID."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM optimization_runs WHERE optimization_id = ?",
                (optimization_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            result = dict(row)

            # Parse JSON fields
            for field in [
                "symbols",
                "timeframes",
                "parameter_space",
                "constraints",
                "best_parameters",
            ]:
                if result.get(field):
                    with contextlib.suppress(json.JSONDecodeError, TypeError):
                        result[field] = json.loads(result[field])

            return result

        except Exception as e:
            logger.error(f"Error getting optimization run: {e}")
            return None
        finally:
            if conn:
                conn.close()

    # -----------------------------------------------------------------------------------------
    # Optimization Results
    # -----------------------------------------------------------------------------------------

    def save_optimization_results(
        self,
        optimization_id: int,
        results: List[Dict[str, Any]],
    ) -> int:
        """
        Bulk saves optimization results (individual backtest summaries).

        Args:
            optimization_id: ID of the run
            results: List of dicts containing:
                - backtest_id (int)
                - parameters (dict)
                - score (float)
                - rank (int)
                - total_trades (int)
                - win_rate (float)
                - profit_factor (float)
                - sharpe_ratio (float)
                - max_drawdown (float)
                - is_best (bool)
                - is_top_10 (bool)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
            INSERT INTO optimization_results (
                optimization_id, backtest_id, parameters,
                score, rank,
                total_trades, win_rate, profit_factor, sharpe_ratio, max_drawdown,
                is_best, is_top_10, overfitting_score, stability_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            data_tuples = []
            for res in results:
                data_tuples.append(
                    (
                        optimization_id,
                        res.get("backtest_id"),
                        json.dumps(res.get("parameters", {})),
                        res.get("score"),
                        res.get("rank"),
                        res.get("total_trades", 0),
                        res.get("win_rate", 0.0),
                        res.get("profit_factor", 0.0),
                        res.get("sharpe_ratio", 0.0),
                        res.get("max_drawdown", 0.0),
                        1 if res.get("is_best") else 0,
                        1 if res.get("is_top_10") else 0,
                        res.get("overfitting_score"),
                        res.get("stability_score"),
                    )
                )

            cursor.executemany(query, data_tuples)

            # If we inserted logic to update optimization_runs summary stats based on this, we could called it here.
            # But usually update_optimization_status is called separately.

            conn.commit()
            return len(data_tuples)

        except Exception as e:
            logger.error(f"Error saving optimization results: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_optimization_results(
        self,
        optimization_id: int,
        limit: int = 100,
        order_by: str = "score",
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """Retrieve results for an optimization run."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            valid_columns = [
                "score",
                "rank",
                "sharpe_ratio",
                "profit_factor",
                "total_trades",
                "win_rate",
            ]
            sort_col = order_by if order_by in valid_columns else "score"
            sort_dir = "ASC" if ascending else "DESC"

            query = f"""
            SELECT * FROM optimization_results
            WHERE optimization_id = ?
            ORDER BY {sort_col} {sort_dir}
            LIMIT ?
            """

            cursor.execute(query, (optimization_id, limit))
            rows = cursor.fetchall()

            results = []
            for row in rows:
                res = dict(row)
                if res.get("parameters"):
                    with contextlib.suppress(Exception):
                        res["parameters"] = json.loads(res["parameters"])
                results.append(res)

            return results

        except Exception as e:
            logger.error(f"Error retrieving optimization results: {e}")
            return []
        finally:
            if conn:
                conn.close()

    # -----------------------------------------------------------------------------------------
    # Walk-Forward Analysis
    # -----------------------------------------------------------------------------------------

    def create_walk_forward_window(
        self,
        optimization_id: int,
        window_number: int,
        train_start: datetime,
        train_end: datetime,
        test_start: datetime,
        test_end: datetime,
        best_parameters: Dict[str, Any],
        train_backtest_id: Optional[int] = None,
        test_backtest_id: Optional[int] = None,
        train_metrics: Optional[Dict[str, float]] = None,
        test_metrics: Optional[Dict[str, float]] = None,
    ) -> int:
        """Create a walk-forward window record.

        Args:
            optimization_id: ID of the optimization run
            window_number: Window sequence number
            train_start: Training period start date
            train_end: Training period end date
            test_start: Testing period start date
            test_end: Testing period end date
            best_parameters: Best parameters found in training
            train_backtest_id: Backtest ID for training run
            test_backtest_id: Backtest ID for testing run
            train_metrics: Training performance metrics
            test_metrics: Testing performance metrics
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate overfitting ratio
            overfitting_ratio = None
            if train_metrics and test_metrics:
                train_return = train_metrics.get("return", 0)
                test_return = test_metrics.get("return", 0)
                if train_return != 0:
                    overfitting_ratio = test_return / train_return

            query = """
            INSERT INTO walk_forward_windows (
                optimization_id, window_number,
                train_start, train_end, test_start, test_end,
                best_parameters,
                train_backtest_id, train_return, train_sharpe, train_drawdown, train_total_trades,
                test_backtest_id, test_return, test_sharpe, test_drawdown, test_total_trades,
                overfitting_ratio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            cursor.execute(
                query,
                (
                    optimization_id,
                    window_number,
                    train_start,
                    train_end,
                    test_start,
                    test_end,
                    json.dumps(best_parameters),
                    train_backtest_id,
                    train_metrics.get("return") if train_metrics else None,
                    train_metrics.get("sharpe") if train_metrics else None,
                    train_metrics.get("drawdown") if train_metrics else None,
                    train_metrics.get("total_trades") if train_metrics else None,
                    test_backtest_id,
                    test_metrics.get("return") if test_metrics else None,
                    test_metrics.get("sharpe") if test_metrics else None,
                    test_metrics.get("drawdown") if test_metrics else None,
                    test_metrics.get("total_trades") if test_metrics else None,
                    overfitting_ratio,
                ),
            )

            window_id = cursor.lastrowid
            if window_id is None:
                raise ValueError("Failed to retrieve window ID after insertion.")

            conn.commit()
            logger.info(
                f"Walk-forward window {window_number} created with ID {window_id}"
            )
            return int(window_id) if window_id is not None else 0

        except Exception as e:
            logger.error(f"Error creating walk-forward window: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def get_walk_forward_windows(self, optimization_id: int) -> List[Dict[str, Any]]:
        """Retrieve all walk-forward windows for an optimization run."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
            SELECT * FROM walk_forward_windows
            WHERE optimization_id = ?
            ORDER BY window_number
            """

            cursor.execute(query, (optimization_id,))
            rows = cursor.fetchall()

            windows = []
            for row in rows:
                window = dict(row)
                if window.get("best_parameters"):
                    with contextlib.suppress(Exception):
                        window["best_parameters"] = json.loads(
                            window["best_parameters"]
                        )
                windows.append(window)

            return windows

        except Exception as e:
            logger.error(f"Error retrieving walk-forward windows: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_walk_forward_summary(
        self, optimization_id: int
    ) -> Optional[Dict[str, Any]]:
        """Calculate summary statistics for a walk-forward analysis.

        Returns:
            Dict containing:
            - total_windows: Number of windows
            - avg_train_return: Average training return
            - avg_test_return: Average testing return
            - avg_overfitting_ratio: Average IS/OOS ratio
            - consistency_score: Percentage of profitable OOS windows
        """
        windows = self.get_walk_forward_windows(optimization_id)

        if not windows:
            return None

        total_windows = len(windows)
        train_returns = [
            w["train_return"] for w in windows if w.get("train_return") is not None
        ]
        test_returns = [
            w["test_return"] for w in windows if w.get("test_return") is not None
        ]
        overfitting_ratios = [
            w["overfitting_ratio"]
            for w in windows
            if w.get("overfitting_ratio") is not None
        ]

        profitable_windows = len([r for r in test_returns if r > 0])

        return {
            "total_windows": total_windows,
            "avg_train_return": (
                sum(train_returns) / len(train_returns) if train_returns else 0
            ),
            "avg_test_return": (
                sum(test_returns) / len(test_returns) if test_returns else 0
            ),
            "avg_train_sharpe": sum(w.get("train_sharpe", 0) for w in windows)
            / total_windows,
            "avg_test_sharpe": sum(w.get("test_sharpe", 0) for w in windows)
            / total_windows,
            "avg_overfitting_ratio": (
                sum(overfitting_ratios) / len(overfitting_ratios)
                if overfitting_ratios
                else 0
            ),
            "consistency_score": (
                (profitable_windows / total_windows * 100) if total_windows > 0 else 0
            ),
            "profitable_windows": profitable_windows,
            "losing_windows": total_windows - profitable_windows,
        }

    # -----------------------------------------------------------------------------------------
    # Monte Carlo Simulations
    # -----------------------------------------------------------------------------------------

    def create_monte_carlo_simulation(
        self,
        backtest_id: int,
        simulation_type: str,
        num_simulations: int,
        block_size: Optional[int] = None,
        random_seed: Optional[int] = None,
    ) -> int:
        """Create a Monte Carlo simulation record.

        Args:
            backtest_id: ID of the backtest to simulate
            simulation_type: Type of simulation (shuffle_trades, resample_returns, bootstrap)
            num_simulations: Number of simulations to run
            block_size: Block size for bootstrap method
            random_seed: Random seed for reproducibility
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = """
            INSERT INTO monte_carlo_simulations (
                backtest_id, simulation_type, num_simulations,
                block_size, random_seed
            ) VALUES (?, ?, ?, ?, ?)
            """

            cursor.execute(
                query,
                (
                    backtest_id,
                    simulation_type,
                    num_simulations,
                    block_size,
                    random_seed,
                ),
            )

            simulation_id = cursor.lastrowid
            if simulation_id is None:
                raise ValueError("Failed to retrieve simulation ID after insertion.")

            conn.commit()
            logger.info(f"Monte Carlo simulation created with ID {simulation_id}")
            return int(simulation_id) if simulation_id is not None else 0

        except Exception as e:
            logger.error(f"Error creating Monte Carlo simulation: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def save_monte_carlo_results(
        self,
        simulation_id: int,
        results: Dict[str, Any],
    ) -> bool:
        """Save Monte Carlo simulation results.

        Args:
            simulation_id: ID of the simulation
            results: Dictionary containing simulation results with keys:
                - mean_return, median_return, std_return
                - ci_95_lower, ci_95_upper, ci_99_lower, ci_99_upper
                - probability_of_profit, probability_of_ruin, expected_shortfall_95
                - percentile_5, percentile_25, percentile_50, percentile_75, percentile_95
                - original_return, original_sharpe, original_max_dd
                - distribution_data (dict with returns, drawdowns, sharpes)
        """
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Serialize distribution data
            distribution_json = None
            if "distribution_data" in results:
                distribution_json = json.dumps(results["distribution_data"])

            query = """
            UPDATE monte_carlo_simulations SET
                mean_return = ?,
                median_return = ?,
                std_return = ?,
                ci_95_lower = ?,
                ci_95_upper = ?,
                ci_99_lower = ?,
                ci_99_upper = ?,
                probability_of_profit = ?,
                probability_of_ruin = ?,
                expected_shortfall_95 = ?,
                percentile_5 = ?,
                percentile_25 = ?,
                percentile_50 = ?,
                percentile_75 = ?,
                percentile_95 = ?,
                original_return = ?,
                original_sharpe = ?,
                original_max_dd = ?,
                distribution_data = ?
            WHERE simulation_id = ?
            """

            cursor.execute(
                query,
                (
                    results.get("mean_return"),
                    results.get("median_return"),
                    results.get("std_return"),
                    results.get("ci_95_lower"),
                    results.get("ci_95_upper"),
                    results.get("ci_99_lower"),
                    results.get("ci_99_upper"),
                    results.get("probability_of_profit"),
                    results.get("probability_of_ruin"),
                    results.get("expected_shortfall_95"),
                    results.get("percentile_5"),
                    results.get("percentile_25"),
                    results.get("percentile_50"),
                    results.get("percentile_75"),
                    results.get("percentile_95"),
                    results.get("original_return"),
                    results.get("original_sharpe"),
                    results.get("original_max_dd"),
                    distribution_json,
                    simulation_id,
                ),
            )

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Error saving Monte Carlo results: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

    def get_monte_carlo_simulation(
        self, simulation_id: int
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a Monte Carlo simulation by ID."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "SELECT * FROM monte_carlo_simulations WHERE simulation_id = ?",
                (simulation_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            result = dict(row)

            # Parse distribution data
            if result.get("distribution_data"):
                with contextlib.suppress(json.JSONDecodeError, TypeError):
                    result["distribution_data"] = json.loads(
                        result["distribution_data"]
                    )

            return result

        except Exception as e:
            logger.error(f"Error getting Monte Carlo simulation: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def save_optimization_summary(
        self,
        strategy_name: str,
        optimization_type: str,
        optimization_method: str,
        start_date: datetime,
        end_date: datetime,
        parameter_space: Dict[str, Any],
        objective_function: str,
        results: List[
            Tuple[Dict[str, Any], float, int]
        ],  # (params, score, backtest_id)
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        n_jobs: int = 1,
        strategy_version: str = "1.0.0",
    ) -> int:
        """Save optimization run summary."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            # Find best result
            best_result = max(results, key=lambda x: x[1]) if results else None
            best_params = best_result[0] if best_result else None
            best_score = best_result[1] if best_result else None
            best_backtest_id = best_result[2] if best_result else None

            # Create optimization run using existing method
            optimization_id = self.create_optimization_run(
                strategy_name=strategy_name,
                strategy_version=strategy_version,
                optimization_type=optimization_type,
                optimization_method=optimization_method,
                start_date=start_date,
                end_date=end_date,
                parameter_space=parameter_space,
                objective_function=objective_function,
                symbols=symbols,
                timeframes=timeframes,
                constraints=constraints,
                total_combinations=len(results),
                n_jobs=n_jobs,
                status="completed",
            )

            # Update best results
            if best_result:
                self.update_optimization_status(
                    optimization_id,
                    status="completed",
                    completed_combinations=len(results),
                    best_backtest_id=best_backtest_id,
                    best_score=best_score,
                    best_parameters=best_params,
                )

            # Save all results
            if results:
                # Sort by score (descending)
                sorted_results = sorted(results, key=lambda x: x[1], reverse=True)

                result_data = []
                for rank, (params, score, backtest_id) in enumerate(sorted_results, 1):
                    # Get key metrics from backtest
                    # Since we are in the mixin, we expect get_backtest_finance_metrics to be available
                    # on self (if mixed into the main DB class) or we might need to handle if it's missing.
                    # Assuming standard SQLiteDatabase composition.
                    if hasattr(self, "get_backtest_finance_metrics"):
                        metrics = self.get_backtest_finance_metrics(backtest_id)
                    else:
                        metrics = {}

                    trade_metrics = metrics.get("trade_metrics", {})
                    ratio_metrics = metrics.get("ratio_metrics", {})
                    drawdown_metrics = metrics.get("drawdown_metrics", {})

                    result_data.append(
                        {
                            "backtest_id": backtest_id,
                            "parameters": params,
                            "score": score,
                            "rank": rank,
                            "total_trades": trade_metrics.get("total_trades", 0),
                            "win_rate": trade_metrics.get("win_rate", 0),
                            "profit_factor": trade_metrics.get("profit_factor", 0),
                            "sharpe_ratio": ratio_metrics.get("sharpe", 0),
                            "max_drawdown": drawdown_metrics.get("max_drawdown", 0),
                            "is_best": rank == 1,
                            "is_top_10": rank <= 10,
                            "overfitting_score": None,
                            "stability_score": None,
                        }
                    )

                self.save_optimization_results(optimization_id, result_data)

            logger.info(f"Saved optimization run (ID: {optimization_id})")
            return optimization_id

        except Exception as e:
            logger.error(f"Error saving optimization summary: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def query_best_parameters(
        self, optimization_id: int, top_n: int = 10, metric: str = "score"
    ) -> List[Dict[str, Any]]:
        """Query best parameters from optimization run."""
        return self.get_optimization_results(
            optimization_id,
            limit=top_n,
            order_by=metric if metric != "score" else "score",
            ascending=False,
        )
