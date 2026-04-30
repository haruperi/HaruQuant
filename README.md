# HaruQuant

A comprehensive quantitative trading platform for backtesting, optimization, and live trading with MetaTrader 5.

## Features

### Core Capabilities
- **Multi-Asset Portfolio Backtesting**: Trade multiple instruments simultaneously with unified account tracking
- **Strategy Development**: Flexible strategy framework with technical indicators
- **Backtesting Engine**: High-performance event-driven simulation with realistic execution
- **Optimization**: Multi-parameter optimization with genetic algorithms and grid search
- **Live Trading**: Integration with MetaTrader 5 for automated trading
- **Data Management**: Historical data loading from MT5 and Dukascopy
- **Risk Management**: Portfolio-level risk controls with correlation monitoring
- **Reporting**: Comprehensive performance analytics and visualization
- **Indicator Automation**: Run entire indicator packages (e.g., TALIB) with one command
- **Simulation Slicing**: Dynamic range adjustment and isolated time-window analysis

### Technical Features
- Event-driven simulation architecture
- Vectorized backtesting for speed
- Commission and slippage modeling
- Stop-loss and take-profit execution
- Maximum Adverse/Favorable Excursion tracking
- Portfolio correlation analysis
- Risk parity and equal-weight allocation
- Database storage with SQLite

---

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/haruquant.git
cd haruquant

# Install dependencies
pip install -r requirements.txt

# Initialize database
python backend/scripts/tools/initialize_database.py
```

### Basic Single-Symbol Backtest

```python
from apps.simulation.simulator import TradeSimulator
from apps.simulation.data import SymbolInfoSimulator, AccountInfoSimulator
from backend.services.strategy.base import BaseStrategy
import pandas as pd

# Load data
data = pd.read_csv('eurusd_h1.csv', parse_dates=['timestamp'], index_col='timestamp')

# Create symbol spec
symbol_spec = SymbolInfoSimulator.from_mt5_symbol('EURUSD')

# Create strategy
class MyStrategy(BaseStrategy):
    def on_init(self):
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        # Calculate indicators
        data['sma_20'] = data['close'].rolling(20).mean()
        data['sma_50'] = data['close'].rolling(50).mean()

        # Generate signals
        data['entry_signal'] = 0
        data.loc[data['sma_20'] > data['sma_50'], 'entry_signal'] = 1  # Buy
        data.loc[data['sma_20'] < data['sma_50'], 'entry_signal'] = -1  # Sell

        data['exit_signal'] = 0
        return data

    def get_signal(self, data: pd.DataFrame, current_index: int):
        if current_index < 50:
            return None

        entry_signal = int(data.iloc[current_index]['entry_signal'])
        if entry_signal == 0:
            return None

        return {
            'entry_signal': entry_signal,
            'exit_signal': 0,
            'type': 'buy' if entry_signal == 1 else 'sell'
        }

# Create simulator
simulator = TradeSimulator(
    simulator_name='EURUSD_Backtest',
    mt5_client=None,  # Backtest mode
    account_info=AccountInfoSimulator(balance=10000.0, equity=10000.0),
    symbols={'EURUSD': symbol_spec}
)

# Run backtest
simulator.run(
    data=data,
    strategy=MyStrategy(),
    symbol='EURUSD',
    volume=0.1,
    commission_per_contract=7.0,
    slippage_points=0.5
)

# Results
print(f"Final Balance: ${simulator._account_data.balance:,.2f}")
print(f"Total Trades: {len(simulator._completed_trades)}")
```

---

## Modern API (`haruquant`)

The modern `hqt` namespace provides a high-level, simplified interface for indicators and strategy execution.

### Indicator Packages
Feed indicators as features to ML models or batch-calculate entire packages:

```python
import haruquant as hqt

# Pull data and run all TALIB indicators
data = hqt.YFData.pull("BTC-USD")
features = data.run("talib", mavp=hqt.run_arg_dict(periods=14))
print(features.shape) # (3046, 175)
```

### Simplified Simulation
Run complex simulations with minimal configuration using the `Portfolio` class:

```python
import haruquant as hqt

# Run a full-year simulation
portfolio = hqt.Portfolio.run({
    "data": {
        "symbols": ["EURUSD"],
        "start": "2020-01-01",
        "end": "2020-12-31"
    }
})

# Display beautiful summary table
print(portfolio.summary())
```

### Simulation Range Slicing
Analyze specific market regimes or isolated time windows without re-running simulations:

```python
# Slice existing portfolio for Q1 analysis
q1_portfolio = portfolio.slice(start="2020-01-01", end="2020-03-31")

# Metrics are instantly recalculated for the new window
print(f"Q1 Profit: ${q1_portfolio.total_profit():.2f}")
print(q1_portfolio.summary())
```

---

## Multi-Asset Portfolio Backtesting

Trade multiple instruments simultaneously with unified risk management.

### Quick Example

```python
from apps.simulation.portfolio import PortfolioStrategy, PortfolioEngine
from apps.simulation.data import SymbolInfoSimulator
import pandas as pd

# 1. Load data for multiple symbols
data = {
    'EURUSD': eurusd_df,  # pd.DataFrame with OHLCV
    'GBPUSD': gbpusd_df,
    'USDJPY': usdjpy_df,
}

# 2. Create symbol specs
symbol_specs = {
    symbol: SymbolInfoSimulator.from_mt5_symbol(symbol)
    for symbol in ['EURUSD', 'GBPUSD', 'USDJPY']
}

# 3. Create strategies
strategies = {
    symbol: MyTrendStrategy(params={'symbol': symbol})
    for symbol in data.keys()
}

# 4. Build portfolio strategy
portfolio_strategy = PortfolioStrategy(
    strategies=strategies,
    symbol_specs=symbol_specs,
    data=data,
    allocation_method='equal_weight'  # or 'risk_parity'
)

# 5. Run portfolio backtest
engine = PortfolioEngine(
    portfolio_strategy=portfolio_strategy,
    initial_balance=30000.0,
    config={
        'portfolio_name': 'Multi-Asset Trend Following',
        'volume': 0.1,
        'commission': 7.0,
        'slippage': 0.5
    }
)

result = engine.run(synchronize_data=True, sync_method='ffill')

# 6. View results
summary = result.get_portfolio_summary()
print(f"Total Return: {summary['total_return_pct']:.2f}%")
print(f"Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {summary['max_drawdown_pct']:.2f}%")

# Per-asset breakdown
for symbol, asset_result in result.asset_results.items():
    print(f"{symbol}: {asset_result.total_return_pct:.2f}%")

# Correlation matrix
corr_matrix = result.get_correlation_matrix()
print(corr_matrix)
```

### Key Features

- **Allocation Methods**: Equal-weight and risk-parity position sizing
- **Data Synchronization**: Automatic alignment across symbols (ffill/drop/interpolate)
- **Portfolio Metrics**: Sharpe ratio, drawdown, correlation analysis
- **Asset Attribution**: Individual performance metrics for each symbol
- **Single Account**: Unified balance and equity tracking

### Documentation

See [Portfolio Backtesting Guide](docs/portfolio_backtesting.md) for complete documentation including:
- Architecture overview
- API reference
- Allocation methods
- Data synchronization
- Best practices
- Advanced examples

---

## Strategy Development

### Creating a Strategy

```python
from backend.services.strategy.base import BaseStrategy
import pandas as pd

class MyCustomStrategy(BaseStrategy):
    def __init__(self, params=None):
        self.params = params or {}
        self.fast_period = self.params.get('fast_period', 20)
        self.slow_period = self.params.get('slow_period', 50)

    def on_init(self) -> None:
        """Initialize strategy (called once)."""
        pass

    def on_bar(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate indicators and generate signals."""
        # Calculate indicators
        data['fast_ma'] = data['close'].rolling(self.fast_period).mean()
        data['slow_ma'] = data['close'].rolling(self.slow_period).mean()

        # Generate signals
        data['entry_signal'] = 0
        data.loc[data['fast_ma'] > data['slow_ma'], 'entry_signal'] = 1
        data.loc[data['fast_ma'] < data['slow_ma'], 'entry_signal'] = -1

        data['exit_signal'] = 0

        return data

    def get_signal(self, data: pd.DataFrame, current_index: int):
        """Return signal for current bar."""
        if current_index < self.slow_period:
            return None

        entry_signal = int(data.iloc[current_index]['entry_signal'])

        if entry_signal == 0:
            return None

        return {
            'entry_signal': entry_signal,
            'exit_signal': 0,
            'type': 'buy' if entry_signal == 1 else 'sell',
            'sl': 50,  # Stop-loss in points
            'tp': 100,  # Take-profit in points
        }
```

---

## Optimization

Optimize strategy parameters with grid search or genetic algorithms.

```python
from apps.optimization.optimizer import GridSearchOptimizer

# Define parameter space
param_space = {
    'fast_period': [10, 20, 30],
    'slow_period': [50, 100, 150],
    'sl_points': [30, 50, 100],
}

# Create optimizer
optimizer = GridSearchOptimizer(
    strategy_class=MyCustomStrategy,
    param_space=param_space,
    data=data,
    symbol='EURUSD',
    initial_balance=10000.0
)

# Run optimization
results = optimizer.optimize(metric='sharpe_ratio')

# View best parameters
best_params = results['best_params']
print(f"Best Parameters: {best_params}")
print(f"Best Sharpe Ratio: {results['best_score']:.2f}")
```

---

## Live Trading

Connect to MetaTrader 5 for automated trading.

```python
from backend.mcp.mt5_mcp.client import MT5Client
from apps.live.portfolio_manager import PortfolioManager

# Connect to MT5
client = MT5Client(
    login=12345678,
    password='your_password',
    server='YourBroker-Live',
    path='C:/Program Files/MetaTrader 5/terminal64.exe'
)

client.initialize()

# Create portfolio manager
portfolio_manager = PortfolioManager(
    client=client,
    strategies={'EURUSD': MyStrategy()},
    config={
        'max_total_exposure': 0.8,
        'max_drawdown_pct': 10.0,
    }
)

# Start trading
portfolio_manager.start()
```

---

## Project Structure

```
HaruQuant/
â”œâ”€â”€ apps/
â”‚   â”œâ”€â”€ simulation/         # Backtesting engine
â”‚   â”‚   â”œâ”€â”€ simulator.py    # TradeSimulator
â”‚   â”‚   â”œâ”€â”€ engine.py       # SimulationEngine
â”‚   â”‚   â”œâ”€â”€ portfolio.py    # PortfolioEngine, PortfolioStrategy
â”‚   â”‚   â”œâ”€â”€ synchronizer.py # DataSynchronizer
â”‚   â”‚   â””â”€â”€ data.py         # SymbolInfoSimulator, AccountInfoSimulator
â”‚   â”œâ”€â”€ strategy/           # Strategy framework
â”‚   â”œâ”€â”€ optimization/       # Parameter optimization
â”‚   â”œâ”€â”€ mt5/                # MetaTrader 5 integration
â”‚   â”œâ”€â”€ live/               # Live trading
â”‚   â”œâ”€â”€ sqlite/             # Database operations
â”‚   â””â”€â”€ api/                # REST API
â”œâ”€â”€ backend/data/
â”‚   â”œâ”€â”€ database/           # SQLite databases
â”‚   â””â”€â”€ strategies/         # Strategy implementations
â”œâ”€â”€ tests/
â”‚   â”œâ”€â”€ unit/               # Unit tests
â”‚   â”œâ”€â”€ integration/        # Integration tests
â”‚   â”œâ”€â”€ performance/        # Performance benchmarks
â”‚   â””â”€â”€ usage/              # Example scripts
â”œâ”€â”€ docs/                   # Documentation
â””â”€â”€ README.md
```

---

## Testing

### Run Unit Tests

```bash
# All unit tests
python -m pytest tests/unit/ -v

# Simulation module tests
python -m pytest tests/unit/simulation/ -v

# Portfolio tests
python -m pytest tests/unit/simulation/test_portfolio*.py -v
```

### Run Integration Tests

```bash
python -m pytest tests/integration/ -v
```

### Run Performance Benchmarks

```bash
# Install pytest-benchmark
pip install pytest-benchmark

# Run benchmarks
python -m pytest tests/performance/ -v --benchmark-only
```

---

## Examples

See `tests/usage/` for comprehensive examples:

- **Basic Backtesting**: `tests/usage/backtest/01_simple_backtest.py`
- **Portfolio Backtesting**: `tests/usage/backtest/07_portfolio_backtest.py`
- **Multi-Asset Examples**: `tests/usage/backtest/05_advanced_features/02_multi_asset.py`
- **Optimization**: `tests/usage/optimization/`
- **Live Trading**: `tests/usage/live/`

---

## API Reference

### Backtesting

- `TradeSimulator`: Main backtesting engine
- `SymbolInfoSimulator`: Symbol specifications
- `AccountInfoSimulator`: Account information

### Portfolio

- `PortfolioStrategy`: Multi-symbol strategy configuration
- `PortfolioEngine`: Multi-asset backtest orchestration
- `PortfolioBacktestResult`: Portfolio results container
- `DataSynchronizer`: Multi-symbol data alignment

### Strategies

- `BaseStrategy`: Base class for all strategies
- `TrendFollowingStrategy`: Example trend-following strategy

### Optimization

- `GridSearchOptimizer`: Grid search parameter optimization
- `GeneticOptimizer`: Genetic algorithm optimization

---

## Performance

### Backtesting Speed

| Scenario | Bars | Time |
|----------|------|------|
| Single symbol | 5000 | ~30s |
| 3 symbols (portfolio) | 5000 | ~90s |
| 5 symbols (portfolio) | 5000 | ~150s |

### Memory Usage

- Single symbol (5000 bars): ~10-50 MB
- Portfolio (5 symbols, 5000 bars): ~100-200 MB

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Ensure all tests pass
5. Submit a pull request

---

## License

[Add your license here]

---

## Contact

- **Project**: HaruQuant
- **Author**: HaruQuant Development Team
- **Email**: [your-email@example.com]

---

## Changelog

### 2026-02-06 - Multi-Asset Portfolio Backtesting

**Added:**
- `PortfolioStrategy` and `PortfolioEngine` for multi-symbol backtesting
- `DataSynchronizer` for data alignment across symbols
- `PortfolioBacktestResult` with correlation analysis
- Equal-weight and risk-parity allocation methods
- Integration tests and performance benchmarks
- Comprehensive documentation

**Updated:**
- `SimulationEngine` to support portfolio mode
- API with portfolio backtest endpoint
- Example files with new implementation

### Earlier Versions

- Simulation engine with event-driven architecture
- Strategy framework and indicator library
- MT5 integration for live trading
- Database storage with SQLite
- REST API for remote execution
- Optimization with grid search and genetic algorithms

---

## Acknowledgments

- MetaTrader 5 for market access
- Dukascopy for historical data
- Community contributors

---

For detailed documentation, see the `docs/` directory or visit the [documentation site](https://your-docs-site.com).

