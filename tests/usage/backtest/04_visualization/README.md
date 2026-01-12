# Visualization Examples

Examples demonstrating plotting and visualization capabilities.

## Examples

### 01_basic_plotting.py
Basic plotting with matplotlib backend.

### 02_custom_themes.py
Using built-in themes (light, dark, grayscale, print).

### 03_interactive_bokeh.py
Interactive plots with Bokeh backend (if installed).

### 04_optimization_heatmaps.py
Visualize optimization results as heatmaps.

### 05_html_reports.py
Generate HTML reports with embedded plots.

## Quick Start

```python
from apps.backtest import Backtest, Strategy
from data_helpers import load_dukascopy

data = load_dukascopy('EURUSD', start_date='2025-11-03')
bt = Backtest(data, MyStrategy, cash=10000)
result = bt.run()

# Simple plot
result.plot()

# Or use backtest plot method
bt.plot()
```

All examples use real Dukascopy data.
