# Optimization Module

**Advanced parameter optimization, validation, and stress testing for trading strategies.**

---

## 📖 Overview

The Optimization Module provides a complete suite of tools for finding optimal strategy parameters, validating robustness, and stress-testing trading systems. It includes:

- **5 Optimization Algorithms:** Grid Search, Random Search, Bayesian Optimization, Genetic Algorithm
- **Validation Tools:** Walk-Forward Analysis
- **Stress Testing:** Monte Carlo Simulation
- **Real-time Progress:** WebSocket-based progress updates
- **Parallel Execution:** Multi-core support for faster optimization
- **Full Persistence:** All runs and results saved to database
- **Modern UI:** React-based frontend with real-time updates

---

## 🏗️ Architecture

```
apps/optimization/
├── __init__.py                  # Module exports
├── models.py                    # Pydantic models for API
├── core.py                      # Background task orchestration
├── result.py                    # OptimizationResult, OptimizationSummary
├── scoring.py                   # Objective functions (Sharpe, Sortino, etc.)
├── parallel.py                  # Parallel execution utilities
├── walk_forward.py              # Walk-forward analysis
├── monte_carlo.py               # Monte Carlo simulation
├── methods/
│   ├── __init__.py
│   ├── grid_search.py          # Exhaustive grid search
│   ├── random_search.py        # Random sampling
│   ├── bayesian.py             # Gaussian Process optimization
│   └── genetic.py              # Evolutionary algorithm
└── docs/                        # Documentation
    ├── README.md               # This file
    ├── QUICK_START.md          # 5-minute quick start
    ├── TESTING_CHECKLIST.md    # Comprehensive testing guide
    ├── COMPLETION_SUMMARY.md   # Implementation status
    └── IMPLEMENTATION_PROGRESS.md # Detailed progress tracking
```

---

## 🚀 Quick Start

### 1. Start Servers

**Backend:**
```bash
cd D:\Trading\Applications\Testing\haruquant
uvicorn apps.api.main:app --reload
```

**Frontend:**
```bash
cd D:\Trading\Applications\Testing\haruquant\ui
npm run dev
```

### 2. Navigate to Optimization Page
Open browser: `http://localhost:3000/optimization`

### 3. Run First Optimization
1. Select a strategy
2. Choose "Grid Search"
3. Add 2 parameters (small ranges for quick test)
4. Click "Start Optimization"
5. Watch real-time progress updates

**See `QUICK_START.md` for detailed instructions.**

---

## 🔧 Optimization Methods

### 1. Grid Search
**Best for:** Small parameter spaces, exhaustive exploration

**How it works:**
- Tests every combination in the parameter grid
- Guaranteed to find global optimum within grid
- Computational cost: O(n^d) where n = steps per parameter, d = dimensions

**Example:**
```python
from apps.optimization.methods import grid_search

summary = grid_search(
    strategy_class=MyStrategy,
    data=df,
    param_grid={
        'fast_period': [10, 15, 20, 25, 30],
        'slow_period': [50, 100, 150, 200]
    },
    scoring_func=sharpe_score,
    initial_balance=10000.0
)
```

**Total combinations:** 5 × 4 = 20

---

### 2. Random Search
**Best for:** Large parameter spaces, quick exploration

**How it works:**
- Randomly samples parameter combinations
- Often finds good solutions faster than grid search
- Computational cost: O(n_iter)

**Example:**
```python
from apps.optimization.methods import random_search

summary = random_search(
    strategy_class=MyStrategy,
    data=df,
    param_distributions={
        'fast_period': (10, 50),   # (min, max)
        'slow_period': (50, 200)
    },
    n_iter=100,
    scoring_func=sharpe_score
)
```

**Total evaluations:** 100 (configurable)

---

### 3. Bayesian Optimization
**Best for:** Expensive objective functions, intelligent search

**How it works:**
- Builds probabilistic model (Gaussian Process) of objective function
- Uses Expected Improvement to guide search
- Balances exploration vs exploitation
- Requires fewer evaluations than random search

**Example:**
```python
from apps.optimization.methods import bayesian_optimization

summary = bayesian_optimization(
    strategy_class=MyStrategy,
    data=df,
    param_space={
        'fast_period': (10, 50),
        'slow_period': (50, 200)
    },
    param_types={
        'fast_period': 'int',
        'slow_period': 'int'
    },
    n_iterations=50,
    n_initial_points=10,  # Random exploration
    scoring_func=sharpe_score
)
```

**Total evaluations:** 10 (random) + 40 (guided) = 50

---

### 4. Genetic Algorithm
**Best for:** Complex parameter spaces, avoiding local optima

**How it works:**
- Evolves population of parameter sets over generations
- Selection: Tournament selection (best individuals survive)
- Crossover: Single-point crossover to create offspring
- Mutation: Gaussian mutation for exploration
- Elitism: Top 10% always preserved

**Example:**
```python
from apps.optimization.methods import genetic_algorithm

summary = genetic_algorithm(
    strategy_class=MyStrategy,
    data=df,
    param_ranges={
        'fast_period': (10, 50),
        'slow_period': (50, 200)
    },
    param_types={
        'fast_period': 'int',
        'slow_period': 'int'
    },
    population_size=50,
    generations=30,
    mutation_rate=0.1,
    crossover_rate=0.8,
    scoring_func=sharpe_score
)
```

**Total evaluations:** 50 × 30 = 1,500

---

## 📊 Validation & Stress Testing

### Walk-Forward Analysis
**Purpose:** Detect overfitting by testing on out-of-sample data

**How it works:**
1. Split data into train/test windows
2. Optimize parameters on train window
3. Test with those parameters on test window
4. Roll forward and repeat
5. Compare in-sample vs out-of-sample performance

**Robustness Score:**
- Average ratio of OOS performance to IS performance
- > 70% = Pass (strategy is robust)
- < 70% = Fail (likely overfit)

**Example:**
```python
from apps.optimization import walk_forward

wf_summary = walk_forward(
    strategy_class=MyStrategy,
    data=df,
    param_grid={'fast_period': [10, 20, 30]},
    train_period=1000,  # bars
    test_period=500,    # bars
    scoring_func=sharpe_score
)

# Check robustness
for window in wf_summary.windows:
    print(f"Window {window.number}:")
    print(f"  IS Return: {window.train_return:.2f}%")
    print(f"  OOS Return: {window.test_return:.2f}%")
    print(f"  Ratio: {window.overfitting_ratio:.2f}")
```

---

### Monte Carlo Simulation
**Purpose:** Quantify uncertainty and assess risk

**How it works:**
1. Take existing backtest results (trades)
2. Randomly resample/shuffle trades
3. Recalculate performance metrics
4. Repeat 1000+ times
5. Analyze distribution of outcomes

**Three Methods:**
- **Bootstrap:** Resample trades with replacement (preserves distribution)
- **Shuffle Trades:** Randomize trade order (breaks serial correlation)
- **Resample Returns:** Resample returns directly

**Output:**
- Confidence intervals (95%, 99%)
- Probability of profit
- Probability of ruin
- Expected shortfall (tail risk)
- Percentile distribution

**Example:**
```python
from apps.optimization import monte_carlo_analysis

mc_result = monte_carlo_analysis(
    result=backtest_result,
    num_simulations=1000,
    simulation_type="bootstrap",
    block_size=10
)

print(f"Original Return: {mc_result.original_return:.2f}%")
print(f"95% CI: [{mc_result.ci_95_lower:.2f}%, {mc_result.ci_95_upper:.2f}%]")
print(f"Probability of Profit: {mc_result.probability_of_profit * 100:.1f}%")
print(f"Probability of Ruin: {mc_result.probability_of_ruin * 100:.2f}%")
```

---

## 🎯 Objective Functions

Available scoring functions in `apps/optimization/scoring.py`:

| Function | Description | Formula | Best When |
|----------|-------------|---------|-----------|
| `sharpe_score` | Risk-adjusted return | (Return - RFR) / Volatility | Default choice |
| `sortino_score` | Downside risk-adjusted | Return / Downside Deviation | Focus on downside |
| `calmar_score` | Return vs max drawdown | Return / Max Drawdown | Drawdown-sensitive |
| `profit_factor_score` | Win/loss ratio | Gross Profit / Gross Loss | High win rate |
| `total_return_score` | Raw return | Total Return % | Absolute returns |

**Custom Objective Functions:**
```python
from apps.backtest.result import BacktestResult

def custom_score(result: BacktestResult) -> float:
    """
    Custom objective function.

    Higher is better. Return -inf for invalid strategies.
    """
    if result.total_trades < 30:
        return float('-inf')  # Insufficient trades

    # Custom formula: Sharpe × Win Rate
    return result.sharpe_ratio * result.win_rate
```

---

## 🌐 API Reference

### REST Endpoints

**Start Optimization:**
```http
POST /api/optimization/runs
Content-Type: application/json

{
  "strategy_id": 1,
  "method": "grid",
  "objective": "sharpe",
  "symbol": "EURUSD",
  "timeframe": "H1",
  "start_date": "2023-01-01",
  "end_date": "2023-12-31",
  "parameters": [
    {"name": "fast_period", "min": 10, "max": 50, "step": 10, "type": "int"}
  ],
  "n_jobs": -1
}
```

**Get Run Details:**
```http
GET /api/optimization/runs/{id}
```

**Get Results:**
```http
GET /api/optimization/runs/{id}/results?limit=100
```

**Cancel Optimization:**
```http
DELETE /api/optimization/runs/{id}
```

### WebSocket

**Connect for Real-time Progress:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/api/optimization/ws/{id}');

ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log(`Progress: ${progress.percentage}%`);
  console.log(`Best Score: ${progress.best_score}`);
};
```

**See API docs:** `http://127.0.0.1:8000/docs`

---

## 📦 Database Schema

### optimization_runs
Stores metadata for each optimization job.

| Column | Type | Description |
|--------|------|-------------|
| optimization_id | INTEGER | Primary key |
| strategy_name | TEXT | Strategy being optimized |
| optimization_method | TEXT | grid, random, bayesian, genetic |
| status | TEXT | pending, running, completed, failed, cancelled |
| total_combinations | INTEGER | Total parameter combinations |
| completed_combinations | INTEGER | Combinations tested so far |
| best_score | REAL | Best objective function value |
| best_parameters | TEXT | JSON of best parameters |
| best_backtest_id | INTEGER | FK to backtest_runs |
| created_at | TIMESTAMP | When optimization started |
| completed_at | TIMESTAMP | When optimization finished |

### optimization_results
Stores results for each parameter combination tested.

| Column | Type | Description |
|--------|------|-------------|
| result_id | INTEGER | Primary key |
| optimization_id | INTEGER | FK to optimization_runs |
| backtest_id | INTEGER | FK to backtest_runs |
| parameters | TEXT | JSON of parameter values |
| score | REAL | Objective function value |
| rank | INTEGER | 1 = best, 2 = second best, etc. |
| sharpe_ratio | REAL | Sharpe ratio for this combo |
| total_return | REAL | Total return % |
| max_drawdown | REAL | Max drawdown % |
| total_trades | INTEGER | Number of trades |
| win_rate | REAL | Win rate (0-1) |
| profit_factor | REAL | Gross profit / gross loss |
| is_best | BOOLEAN | True if rank = 1 |
| is_top_10 | BOOLEAN | True if rank <= 10 |

---

## 🔍 Frontend Components

### OptimizationConfig
**Location:** `ui/src/components/optimization/optimization-config.tsx`

**Features:**
- Strategy selection
- Method dropdown (Grid, Random, Bayesian, Genetic)
- Objective function selection
- Data configuration (symbol, timeframe, dates)
- Dynamic parameter ranges (add/remove/edit)
- Method-specific settings (iterations, population size, etc.)
- Total combinations calculator
- Worker/parallel execution settings

### OptimizationResults
**Location:** `ui/src/components/optimization/optimization-results.tsx`

**Features:**
- Ranked results table with all metrics
- Dynamic parameter columns
- Interactive heatmap visualization
- Sortable by any metric
- Export to CSV (planned)

### WalkForwardAnalysis
**Location:** `ui/src/components/optimization/walk-forward-analysis.tsx`

**Features:**
- Configuration panel (train/test periods)
- Bar chart: In-Sample vs Out-of-Sample
- Robustness score calculation
- Pass/Fail badge
- Window-by-window breakdown

### MonteCarloSimulation
**Location:** `ui/src/components/optimization/monte-carlo-simulation.tsx`

**Features:**
- Backtest ID input
- Simulation count selector (100, 500, 1000, 5000)
- Method selector (Bootstrap, Shuffle, Resample)
- Confidence intervals (95%, 99%)
- Risk metrics display
- Percentile distribution

---

## 🧪 Testing

**See comprehensive testing guide:** `TESTING_CHECKLIST.md`

**Quick smoke test:**
```bash
# 1. Start servers
uvicorn apps.api.main:app --reload
cd ui && npm run dev

# 2. Navigate to http://localhost:3000/optimization

# 3. Configure small grid search (2x2 = 4 combinations)

# 4. Verify:
# - Progress updates in real-time
# - WebSocket connects (green indicator)
# - Results display after completion
# - Database has 4 backtest runs
```

---

## 🐛 Troubleshooting

### Optimization Starts But No Progress
**Cause:** WebSocket not connecting
**Fix:** Check browser console for WS errors, verify backend logs

### "No data loaded for SYMBOL TIMEFRAME"
**Cause:** Missing data files
**Fix:** Ensure Dukascopy data exists for the specified symbol/timeframe/date range

### Progress Stuck at 0%
**Cause:** Strategy class loading failure
**Fix:** Check backend logs, verify strategy exists and is valid

### Results Not Saving to Database
**Cause:** Database write permissions or schema issues
**Fix:** Check database file permissions, verify schema is up to date

---

## 📚 Documentation

- **Quick Start:** `QUICK_START.md` - Get testing in 5 minutes
- **Testing Guide:** `TESTING_CHECKLIST.md` - Comprehensive test plan
- **Implementation Status:** `IMPLEMENTATION_PROGRESS.md` - Detailed progress tracking
- **Completion Summary:** `COMPLETION_SUMMARY.md` - Overview of what's complete
- **API Docs:** `http://127.0.0.1:8000/docs` - Interactive API documentation

---

## 🎯 Performance Tips

1. **Use Vectorized Engine:** Set `engine_type="vectorized"` (5-10x faster than event-driven)
2. **Parallel Execution:** Set `n_jobs=-1` to use all CPU cores
3. **Start Small:** Test with 10-20 combinations first, then scale up
4. **Limit Date Range:** Use 1-3 months for testing, full year for production
5. **Progress Batching:** For large grids (1000+ combos), consider progress updates every 10 iterations

**Benchmarks (approximate):**
- Small grid (10 combos): < 1 minute
- Medium grid (50 combos): 2-5 minutes
- Large grid (200 combos): 10-20 minutes
- Very large grid (1000 combos): 1-2 hours (with n_jobs=-1)

---

## 🚀 Roadmap

### Completed ✅
- [x] Module restructuring
- [x] All 5 optimization methods
- [x] Walk-Forward Analysis
- [x] Monte Carlo Simulation
- [x] WebSocket real-time updates
- [x] Full frontend integration
- [x] Database persistence

### In Progress ⏳
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] UI polish

### Planned 📋
- [ ] ETA (estimated time remaining) display
- [ ] Export results to CSV/JSON
- [ ] Multi-objective optimization (Pareto frontier)
- [ ] Advanced parameter constraints
- [ ] Strategy comparison tool
- [ ] Historical optimization runs viewer
- [ ] Email notifications on completion
- [ ] Distributed optimization (cluster support)

---

## 🤝 Contributing

When adding new optimization methods:

1. Create new file in `apps/optimization/methods/`
2. Implement function signature:
   ```python
   def my_new_method(
       strategy_class,
       data,
       param_space,
       scoring_func,
       initial_balance=10000.0,
       engine_type="vectorized",
       verbose=True,
       progress_callback=None
   ) -> OptimizationSummary:
       """Your optimization algorithm."""
       pass
   ```
3. Call `progress_callback(completed, total, current_params, best_score, best_params)` regularly
4. Return `OptimizationSummary` with all results ranked
5. Add to `apps/optimization/methods/__init__.py` exports
6. Update `apps/optimization/core.py` to handle new method
7. Add to frontend dropdown in `optimization-config.tsx`

---

## 📄 License

Part of HaruQuant trading platform.

---

## 📞 Support

- **Issues:** Create GitHub issue
- **Docs:** See documentation files in `apps/optimization/`
- **API:** `http://127.0.0.1:8000/docs` when server running

---

**Happy Optimizing! 🎉**
