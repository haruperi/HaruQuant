"""
Genetic Algorithm Optimization.

Evolves a population of parameter sets over multiple generations.
Uses tournament selection, crossover, mutation, and elitism.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import numpy as np

import apps.backtest.stats as stats
from apps.backtest.engine import BaseEngine, EventDrivenEngine, VectorizedEngine
from apps.backtest.result import BacktestResult
from apps.logger import logger
from apps.strategy import BaseStrategy

from ..result import OptimizationResult, OptimizationSummary
from ..scoring import sharpe_score


def genetic_algorithm(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,  # pd.DataFrame
    param_ranges: Dict[str, Tuple[float, float]],
    param_types: Optional[Dict[str, str]] = None,
    population_size: int = 50,
    generations: int = 30,
    mutation_rate: float = 0.1,
    crossover_rate: float = 0.8,
    elitism_ratio: float = 0.1,
    tournament_size: int = 3,
    initial_balance: float = 10000.0,
    scoring_func: Callable[[BacktestResult], float] = sharpe_score,
    engine_type: str = "vectorized",
    max_workers: Optional[
        int
    ] = None,  # Not used (Genetic evolution is inherently sequential)
    random_state: Optional[int] = None,
    verbose: bool = True,
    progress_callback: Optional[Callable] = None,
    symbol: Optional[str] = None,
) -> OptimizationSummary:
    """
    Genetic algorithm optimization.

    Evolves a population of parameter sets to find optimal values.

    Args:
        strategy_class: Strategy class to optimize
        data: OHLCV DataFrame
        param_ranges: Dict of param names to (min, max) tuples
        param_types: Dict of param names to "int" or "float" (default: infer)
        population_size: Number of individuals in population
        generations: Number of generations to evolve
        mutation_rate: Probability of mutation (0-1)
        crossover_rate: Probability of crossover (0-1)
        elitism_ratio: Ratio of top individuals to preserve (0-1)
        tournament_size: Number of individuals in tournament selection
        initial_balance: Starting balance
        scoring_func: Function to score results
        engine_type: "vectorized" or "event_driven"
        random_state: Random seed for reproducibility
        verbose: Print progress
        progress_callback: Optional callback(completed, total, current_params, best_score, best_params)

    Returns:
        OptimizationSummary with results

    Example:
        >>> param_ranges = {
        ...     'ema_fast': (5, 30),
        ...     'ema_slow': (30, 150),
        ...     'atr_period': (10, 20)
        ... }
        >>> param_types = {'ema_fast': 'int', 'ema_slow': 'int', 'atr_period': 'int'}
        >>> summary = genetic_algorithm(
        ...     TrendFollowingStrategy,
        ...     data,
        ...     param_ranges,
        ...     param_types=param_types,
        ...     population_size=50,
        ...     generations=30
        ... )
    """
    if random_state is not None:
        np.random.seed(random_state)

    if verbose:
        logger.info("Starting genetic algorithm optimization")
        logger.info(f"Population: {population_size}, Generations: {generations}")
        logger.info(f"Parameter ranges: {param_ranges}")

    # Infer param types if not provided
    if param_types is None:
        param_types = {}
        for param_name, (min_val, max_val) in param_ranges.items():
            if isinstance(min_val, int) and isinstance(max_val, int):
                param_types[param_name] = "int"
            else:
                param_types[param_name] = "float"

    param_names = list(param_ranges.keys())
    n_params = len(param_names)
    n_elites = max(1, int(population_size * elitism_ratio))

    # Storage for all evaluated individuals
    all_results = []
    best_score_so_far = float("-inf")
    best_params_so_far = None
    total_evaluations = population_size * generations
    completed = 0

    start_time = time.time()

    # Get symbol (prefer explicit parameter, fallback to data.name)
    # Note: data.name may not be preserved during pickling for multiprocessing
    if not symbol:
        symbol = data.name if hasattr(data, "name") else "UNKNOWN"

    def create_individual() -> np.ndarray:
        """Create a random individual (parameter vector)."""
        individual = np.zeros(n_params)
        for i, param_name in enumerate(param_names):
            min_val, max_val = param_ranges[param_name]
            if param_types.get(param_name) == "int":
                individual[i] = np.random.randint(min_val, max_val + 1)
            else:
                individual[i] = np.random.uniform(min_val, max_val)
        return individual

    def individual_to_params(individual: np.ndarray) -> Dict[str, Any]:
        """Convert individual array to parameter dict."""
        params = {}
        for i, param_name in enumerate(param_names):
            value = individual[i]
            if param_types.get(param_name) == "int":
                value = int(round(value))
            params[param_name] = value
        return params

    def evaluate_fitness(individual: np.ndarray) -> float:
        """Evaluate fitness of an individual."""
        nonlocal completed, best_score_so_far, best_params_so_far

        params = individual_to_params(individual)

        try:
            # Create strategy
            full_params = params.copy()
            full_params["symbol"] = symbol
            strategy = strategy_class(params=full_params)

            # Run backtest
            engine: BaseEngine
            if engine_type == "vectorized":
                engine = VectorizedEngine(
                    strategy, data, initial_balance=initial_balance
                )
            else:
                engine = EventDrivenEngine(
                    strategy, data, initial_balance=initial_balance
                )

            result = engine.run()

            # Metrics and score
            result_metrics = stats.calculate_all_metrics(result)
            score = scoring_func(result)

            # Store result
            opt_result = OptimizationResult(
                parameters=params.copy(),
                result=result,
                metrics=result_metrics,
                score=score,
            )
            all_results.append(opt_result)

            # Track best
            if score > best_score_so_far:
                best_score_so_far = score
                best_params_so_far = params.copy()

            # Progress callback
            if progress_callback:
                progress_callback(
                    completed=completed + 1,
                    total=total_evaluations,
                    current_params=params,
                    best_score=best_score_so_far,
                    best_params=best_params_so_far,
                )

            completed += 1
            return score

        except Exception as e:
            logger.error(f"Failed for params {params}: {e}")
            completed += 1
            return float("-inf")  # Bad fitness

    def tournament_selection(
        population: List[np.ndarray], fitness: List[float]
    ) -> np.ndarray:
        """Select parent using tournament selection."""
        tournament_indices = np.random.choice(
            len(population), size=tournament_size, replace=False
        )
        tournament_fitness = [fitness[i] for i in tournament_indices]
        winner_idx = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_idx].copy()

    def crossover(
        parent1: np.ndarray, parent2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Single-point crossover."""
        if np.random.random() < crossover_rate:
            point = np.random.randint(1, n_params)
            child1 = np.concatenate([parent1[:point], parent2[point:]])
            child2 = np.concatenate([parent2[:point], parent1[point:]])
            return child1, child2
        else:
            return parent1.copy(), parent2.copy()

    def mutate(individual: np.ndarray) -> np.ndarray:
        """Gaussian mutation."""
        mutated = individual.copy()
        for i, param_name in enumerate(param_names):
            if np.random.random() < mutation_rate:
                min_val, max_val = param_ranges[param_name]
                range_size = max_val - min_val

                # Gaussian mutation with std = 10% of range
                mutation = np.random.normal(0, range_size * 0.1)
                mutated[i] += mutation

                # Clip to bounds
                mutated[i] = np.clip(mutated[i], min_val, max_val)

                # Round if integer parameter
                if param_types.get(param_name) == "int":
                    mutated[i] = round(mutated[i])

        return mutated

    # Initialize population
    if verbose:
        logger.info("Initializing population...")

    population = [create_individual() for _ in range(population_size)]

    # Evolve over generations
    for gen in range(generations):
        if verbose:
            logger.info(f"Generation {gen + 1}/{generations}")

        # Evaluate fitness
        fitness = [evaluate_fitness(ind) for ind in population]

        # Sort by fitness (descending)
        sorted_indices = np.argsort(fitness)[::-1]
        population = [population[i] for i in sorted_indices]
        fitness = [fitness[i] for i in sorted_indices]

        if verbose:
            logger.info(
                f"  Best fitness: {fitness[0]:.4f}, Avg: {np.mean(fitness):.4f}"
            )

        # Create next generation
        next_population = []

        # Elitism: preserve top individuals
        next_population.extend(population[:n_elites])

        # Generate offspring
        while len(next_population) < population_size:
            # Select parents
            parent1 = tournament_selection(population, fitness)
            parent2 = tournament_selection(population, fitness)

            # Crossover
            child1, child2 = crossover(parent1, parent2)

            # Mutation
            child1 = mutate(child1)
            child2 = mutate(child2)

            next_population.append(child1)
            if len(next_population) < population_size:
                next_population.append(child2)

        population = next_population

    # Final evaluation of best individual (if not already done)
    # The best is already in all_results from evolution

    # Rank all results
    all_results.sort(key=lambda x: x.score, reverse=True)
    for i, opt_result in enumerate(all_results):
        opt_result.rank = i + 1

    best = all_results[0] if all_results else None
    duration = time.time() - start_time

    summary = OptimizationSummary(
        best_params=best.parameters if best else {},
        best_score=best.score if best else 0.0,
        best_result=best.result if best else None,
        all_results=all_results,
        total_combinations=total_evaluations,
        completed=completed,
        failed=total_evaluations - completed,
        duration_seconds=duration,
    )

    if verbose:
        logger.success(f"Genetic algorithm complete in {duration:.2f}s")
        logger.info(f"Best params: {summary.best_params}")
        logger.info(f"Best score: {summary.best_score:.4f}")
        logger.info(f"Total evaluations: {completed}/{total_evaluations}")

    return summary
