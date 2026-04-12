"""
Genetic Algorithm Optimization.

Evolves a population of parameter sets over multiple generations.
Uses tournament selection, crossover, mutation, and elitism.
"""

import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

import numpy as np

from backend.common.logger import logger
from backend.services.strategy import BaseStrategy

from ..execution import run_strategy_backtest
from ..result import OptimizationResult, OptimizationSummary
from ..scoring import sharpe_score

BacktestResult = Any


def genetic_algorithm(  # noqa: C901
    strategy_class: Type[BaseStrategy],
    data,
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
    max_workers: Optional[int] = None,
    random_state: Optional[int] = None,
    verbose: bool = True,
    progress_callback: Optional[Callable] = None,
    symbol: Optional[str] = None,
) -> OptimizationSummary:
    """Genetic algorithm optimization."""
    _ = max_workers
    if random_state is not None:
        np.random.seed(random_state)

    if verbose:
        logger.info("Starting genetic algorithm optimization")
        logger.info(f"Population: {population_size}, Generations: {generations}")
        logger.info(f"Parameter ranges: {param_ranges}")

    if param_types is None:
        param_types = {}
        for param_name, (min_val, max_val) in param_ranges.items():
            param_types[param_name] = "int" if isinstance(min_val, int) and isinstance(max_val, int) else "float"

    param_names = list(param_ranges.keys())
    n_params = len(param_names)
    n_elites = max(1, int(population_size * elitism_ratio))

    all_results = []
    best_score_so_far = float("-inf")
    best_params_so_far = None
    total_evaluations = population_size * generations
    completed = 0
    start_time = time.time()

    if not symbol:
        symbol = data.name if hasattr(data, "name") else "UNKNOWN"

    def create_individual() -> np.ndarray:
        individual = np.zeros(n_params)
        for i, param_name in enumerate(param_names):
            min_val, max_val = param_ranges[param_name]
            if param_types.get(param_name) == "int":
                individual[i] = np.random.randint(min_val, max_val + 1)
            else:
                individual[i] = np.random.uniform(min_val, max_val)
        return individual

    def individual_to_params(individual: np.ndarray) -> Dict[str, Any]:
        params = {}
        for i, param_name in enumerate(param_names):
            value = individual[i]
            if param_types.get(param_name) == "int":
                value = int(round(value))
            params[param_name] = value
        return params

    def evaluate_fitness(individual: np.ndarray) -> float:
        nonlocal completed, best_score_so_far, best_params_so_far

        params = individual_to_params(individual)

        try:
            result = run_strategy_backtest(
                strategy_class=strategy_class,
                data=data,
                symbol=symbol,
                params=params,
                initial_balance=initial_balance,
                engine_type=engine_type,
                position_size=0.1,
            )
            result_metrics = result.summary()
            score = scoring_func(result)

            opt_result = OptimizationResult(
                parameters=params.copy(),
                result=result,
                metrics=result_metrics,
                score=score,
            )
            all_results.append(opt_result)

            if score > best_score_so_far:
                best_score_so_far = score
                best_params_so_far = params.copy()

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
            return float("-inf")

    def tournament_selection(
        population: List[np.ndarray], fitness: List[float]
    ) -> np.ndarray:
        tournament_indices = np.random.choice(
            len(population), size=tournament_size, replace=False
        )
        tournament_fitness = [fitness[i] for i in tournament_indices]
        winner_idx = tournament_indices[np.argmax(tournament_fitness)]
        return population[winner_idx].copy()

    def crossover(
        parent1: np.ndarray, parent2: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        if np.random.random() < crossover_rate and n_params > 1:
            point = np.random.randint(1, n_params)
            child1 = np.concatenate([parent1[:point], parent2[point:]])
            child2 = np.concatenate([parent2[:point], parent1[point:]])
            return child1, child2
        return parent1.copy(), parent2.copy()

    def mutate(individual: np.ndarray) -> np.ndarray:
        mutated = individual.copy()
        for i, param_name in enumerate(param_names):
            if np.random.random() < mutation_rate:
                min_val, max_val = param_ranges[param_name]
                range_size = max_val - min_val
                mutation = np.random.normal(0, range_size * 0.1)
                mutated[i] += mutation
                mutated[i] = np.clip(mutated[i], min_val, max_val)
                if param_types.get(param_name) == "int":
                    mutated[i] = round(mutated[i])
        return mutated

    if verbose:
        logger.info("Initializing population...")

    population = [create_individual() for _ in range(population_size)]

    for gen in range(generations):
        if verbose:
            logger.info(f"Generation {gen + 1}/{generations}")

        fitness = [evaluate_fitness(ind) for ind in population]

        sorted_indices = np.argsort(fitness)[::-1]
        population = [population[i] for i in sorted_indices]
        fitness = [fitness[i] for i in sorted_indices]

        if verbose:
            logger.info(
                f"  Best fitness: {fitness[0]:.4f}, Avg: {np.mean(fitness):.4f}"
            )

        next_population = []
        next_population.extend(population[:n_elites])

        while len(next_population) < population_size:
            parent1 = tournament_selection(population, fitness)
            parent2 = tournament_selection(population, fitness)
            child1, child2 = crossover(parent1, parent2)
            child1 = mutate(child1)
            child2 = mutate(child2)
            next_population.append(child1)
            if len(next_population) < population_size:
                next_population.append(child2)

        population = next_population

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
        failed=max(0, total_evaluations - completed),
        duration_seconds=duration,
    )

    if verbose:
        logger.success(f"Genetic algorithm complete in {duration:.2f}s")
        logger.info(f"Best params: {summary.best_params}")
        logger.info(f"Best score: {summary.best_score:.4f}")
        logger.info(f"Total evaluations: {completed}/{total_evaluations}")

    return summary
