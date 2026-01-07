# Plotting Module Documentation

## Overview

The plotting module provides comprehensive visualization capabilities for backtesting results. It supports multiple backends (Matplotlib and Bokeh), various chart types, and extensive customization options.

## Key Features

- 📊 **Multiple Chart Types**: OHLC, equity curves, heatmaps, distributions, and more
- 🎨 **Multiple Backends**: Matplotlib (static) and Bokeh (interactive)
- 🎭 **Theming System**: Pre-built themes (default, dark, minimal) and custom themes
- 📈 **Performance Visualization**: Returns, drawdowns, Sharpe ratios, and more
- 🔍 **Trade Analysis**: Entry/exit markers, P&L charts, win/loss streaks
- 📅 **Monthly Heatmaps**: QuantStats-style calendar returns
- 🔄 **Optimization Analysis**: Parameter heatmaps with marginal distributions
- 📄 **HTML Reports**: Comprehensive reports with embedded charts
- 🌐 **Plotly Conversion**: Convert Matplotlib figures to interactive Plotly charts

## Quick Start

### Basic Plotting

```python
from apps.backtest import Backtest
from apps.plotting import plot

# Run backtest
bt = Backtest(data, MyStrategy, cash=10000)
results = bt.run()

# Create comprehensive plot
fig = plot(results, filename='backtest.png')
```

### Custom Plot Configuration

```python
# Configure what to plot
fig = plot(
    results,
    plot_equity=True,
    plot_drawdown=True,
    plot_returns=True,
    plot_trades=True,
    backend='matplotlib',
    figsize=(15, 10)
)
```

### Interactive Bokeh Plot

```python
# Use Bokeh for interactive charts
fig = plot(
    results,
    backend='bokeh',
    plot_width=1400,
    plot_height=900
)
```

## Module Structure

```
plotting/
├── __init__.py          # Main exports and package interface
├── main.py              # Primary plot() function
├── core.py              # Configuration, colors, formatters
├── charts.py            # OHLC, line, volume charts
├── performance.py       # Equity, returns, P&L
├── drawdown.py          # Drawdown analysis
├── heatmap.py           # Monthly returns, optimization heatmaps
├── distribution.py      # Histograms, QQ plots
├── trades.py            # Trade analysis plots
├── markers.py           # Trade entry/exit markers
├── indicators.py        # Indicator overlays
├── rolling.py           # Rolling metrics (Sharpe, volatility)
├── summary.py           # Summary snapshots
├── themes.py            # Theme management
├── interactive.py       # Bokeh interactive features
├── batch.py             # Batch plotting and HTML reports
├── output.py            # Output handling and file management
├── plotly_convert.py    # Plotly conversion utilities
├── optimization.py      # Optimization result visualization
└── wrappers.py          # Convenience wrapper functions
```

## Chart Types

### 1. Price Charts (charts.py)

**OHLC/Candlestick Chart**

```python
from apps.plotting.charts import _plot_ohlc_matplotlib

fig, ax = plt.subplots(figsize=(12, 6))
_plot_ohlc_matplotlib(ax, ohlc_data, color_mode='color')
```

**Line Chart**

```python
from apps.plotting.charts import _plot_line_chart

fig, ax = plt.subplots(figsize=(12, 6))
_plot_line_chart(ax, data, label='Price', color='blue')
```

**Volume Chart**

```python
from apps.plotting.charts import _plot_volume

fig, ax = plt.subplots(figsize=(12, 3))
_plot_volume(ax, ohlc_data, color_mode='color')
```

### 2. Performance Charts (performance.py)

**Equity Curve**

```python
from apps.plotting.performance import _plot_equity_curve

fig, ax = plt.subplots(figsize=(12, 6))
_plot_equity_curve(ax, equity_series, benchmark=benchmark_series)
```

**Cumulative Returns**

```python
from apps.plotting.performance import _plot_cumulative_returns

fig, ax = plt.subplots(figsize=(12, 6))
_plot_cumulative_returns(ax, returns_series)
```

**Per-Trade P&L**

```python
from apps.plotting.performance import _plot_pnl_chart

fig, ax = plt.subplots(figsize=(12, 6))
_plot_pnl_chart(ax, trades_list)
```

### 3. Drawdown Analysis (drawdown.py)

**Drawdown Chart**

```python
from apps.plotting.drawdown import _plot_drawdown

fig, ax = plt.subplots(figsize=(12, 6))
_plot_drawdown(ax, equity_series)
```

**Underwater Plot**

```python
from apps.plotting.drawdown import _plot_underwater

fig, ax = plt.subplots(figsize=(12, 4))
_plot_underwater(ax, equity_series)
```

### 4. Heatmaps (heatmap.py)

**Monthly Returns Heatmap**

```python
from apps.plotting.heatmap import _plot_monthly_heatmap

fig, ax = plt.subplots(figsize=(12, 6))
_plot_monthly_heatmap(ax, returns_series, show_ytd=True)
```

**Optimization Heatmaps**

```python
from apps.plotting.heatmap import plot_heatmaps

fig = plot_heatmaps(
    optimization_results,
    metric_column='sharpe_ratio',
    show_marginals=True
)
```

### 5. Distribution Analysis (distribution.py)

**Returns Distribution**

```python
from apps.plotting.distribution import _plot_distribution

fig, ax = plt.subplots(figsize=(10, 6))
_plot_distribution(ax, returns_series)
```

**Histogram**

```python
from apps.plotting.distribution import _plot_histogram

fig, ax = plt.subplots(figsize=(10, 6))
_plot_histogram(ax, returns_series, bins=50)
```

**QQ Plot**

```python
from apps.plotting.distribution import _plot_qq

fig, ax = plt.subplots(figsize=(8, 8))
_plot_qq(ax, returns_series)
```

### 6. Trade Analysis (trades.py)

**Trade Duration Analysis**

```python
from apps.plotting.trades import _plot_trade_durations

fig, ax = plt.subplots(figsize=(10, 6))
_plot_trade_durations(ax, trades_list)
```

**Win/Loss Streaks**

```python
from apps.plotting.trades import _plot_win_loss_streaks

fig, ax = plt.subplots(figsize=(12, 6))
_plot_win_loss_streaks(ax, trades_list)
```

**Trade Scatter Plot**

```python
from apps.plotting.trades import _plot_trade_scatter

fig, ax = plt.subplots(figsize=(10, 8))
_plot_trade_scatter(ax, trades_list)
```

### 7. Rolling Metrics (rolling.py)

**Rolling Sharpe Ratio**

```python
from apps.plotting.rolling import _plot_rolling_sharpe

fig, ax = plt.subplots(figsize=(12, 6))
_plot_rolling_sharpe(ax, returns_series, window=252)
```

**Rolling Volatility**

```python
from apps.plotting.rolling import _plot_rolling_volatility

fig, ax = plt.subplots(figsize=(12, 6))
_plot_rolling_volatility(ax, returns_series, window=30)
```

## Theming System

### Available Themes

1. **default** - Clean, professional theme with blue accents
2. **dark** - Dark background for reduced eye strain
3. **minimal** - Minimal styling for publication-ready charts

### Using Themes

```python
from apps.plotting import set_theme, plot

# Set theme globally
set_theme('dark')

# Plot will use dark theme
fig = plot(results)

# Temporary theme context
from apps.plotting import theme_context

with theme_context('minimal'):
    fig = plot(results)
# Reverts to previous theme after context
```

### Creating Custom Themes

```python
from apps.plotting import create_custom_theme

custom_theme = create_custom_theme(
    name='my_theme',
    background_color='#ffffff',
    text_color='#000000',
    grid_color='#cccccc',
    profit_color='#00ff00',
    loss_color='#ff0000',
    font_family='Arial',
    font_size=10
)

set_theme('my_theme')
```

### Theme Colors

```python
from apps.plotting import get_theme_colors

colors = get_theme_colors()
# Returns: {
#     'background': '#ffffff',
#     'text': '#2c3e50',
#     'grid': '#ecf0f1',
#     'profit': '#2ecc71',
#     'loss': '#e74c3c',
#     'candle_up': '#2ecc71',
#     'candle_down': '#e74c3c',
#     ...
# }
```

## Batch Plotting & Reports

### Generate All Plots

```python
from apps.plotting import plot_all

figures = plot_all(
    results,
    output_dir='output/plots',
    formats=['png', 'svg'],
    dpi=300
)
```

### Create HTML Report

```python
from apps.plotting import create_html_report

html_path = create_html_report(
    results,
    output_path='reports/backtest_report.html',
    title='My Strategy Backtest',
    include_stats=True,
    open_browser=True
)
```

## Interactive Features (Bokeh)

### Add Hover Tooltips

```python
from apps.plotting.interactive import add_ohlc_hover

# Bokeh figure with OHLC hover
p = bokeh_figure(...)
add_ohlc_hover(p, data)
```

### Linked Crosshair

```python
from apps.plotting.interactive import add_linked_crosshair

# Link crosshair across multiple plots
figs = [fig1, fig2, fig3]
add_linked_crosshair(figs)
```

### Range Selector

```python
from apps.plotting.interactive import create_range_selector_layout

# Create main plot with range selector
layout = create_range_selector_layout(
    main_figure=main_plot,
    data=equity_series,
    selector_height=100
)
```

## Plotly Conversion

### Convert to Interactive Plotly

```python
from apps.plotting import to_plotly

# Create matplotlib figure
fig = plot(results, backend='matplotlib')

# Convert to Plotly
plotly_fig = to_plotly(fig)
plotly_fig.show()
```

### Save as Interactive HTML

```python
from apps.plotting import save_plotly_html

save_plotly_html(
    plotly_fig,
    filename='interactive_chart.html',
    auto_open=True
)
```

## Output Management

### Save Multiple Formats

```python
from apps.plotting import save_multiple_formats

save_multiple_formats(
    fig,
    basename='backtest_result',
    formats=['png', 'svg', 'pdf'],
    output_dir='output',
    dpi=300
)
```

### Handle Output Automatically

```python
from apps.plotting import handle_plot_output

fig = plot(results)
handle_plot_output(
    fig,
    filename='auto_save.png',
    show=True,
    auto_open=False
)
```

## Convenience Wrappers

Quick access to common plots without full backtest results:

```python
from apps.plotting import (
    plot_returns,
    plot_drawdown,
    plot_monthly_heatmap,
    plot_rolling_sharpe
)

# Plot returns distribution
plot_returns(returns_series, filename='returns.png')

# Plot drawdown
plot_drawdown(equity_series, filename='drawdown.png')

# Plot monthly heatmap
plot_monthly_heatmap(returns_series, filename='monthly.png')

# Plot rolling Sharpe
plot_rolling_sharpe(returns_series, window=252)
```

## Configuration

### Initialize Plotting System

```python
from apps.plotting import initialize_plotting

# Initialize with default settings
initialize_plotting()

# Initialize with custom settings
initialize_plotting(
    backend='matplotlib',
    theme='dark',
    dpi=150,
    style='seaborn-v0_8-darkgrid'
)
```

### Configure Matplotlib

```python
from apps.plotting import configure_matplotlib

configure_matplotlib(
    style='seaborn-v0_8-whitegrid',
    font_size=10,
    figure_facecolor='white',
    axes_facecolor='white'
)
```

### Configure Bokeh

```python
from apps.plotting import configure_bokeh

configure_bokeh(
    output_backend='canvas',  # or 'svg', 'webgl'
    sizing_mode='stretch_width',
    toolbar_location='above'
)
```

## Color Schemes

### Trading Colors

```python
from apps.plotting import TRADING_COLORS

# Access predefined trading colors
profit_color = TRADING_COLORS['profit']    # '#2ecc71'
loss_color = TRADING_COLORS['loss']        # '#e74c3c'
long_color = TRADING_COLORS['long']        # '#3498db'
short_color = TRADING_COLORS['short']      # '#e67e22'
```

### Flat UI Colors

```python
from apps.plotting import FLATUI_COLORS

# Modern flat design colors
turquoise = FLATUI_COLORS['turquoise']     # '#1abc9c'
emerald = FLATUI_COLORS['emerald']         # '#2ecc71'
peter_river = FLATUI_COLORS['peter_river'] # '#3498db'
```

### Grayscale Colors

```python
from apps.plotting import GRAYSCALE_COLORS

# Grayscale palette for publications
black = GRAYSCALE_COLORS['black']          # '#2c3e50'
dark_gray = GRAYSCALE_COLORS['dark_gray']  # '#7f8c8d'
light_gray = GRAYSCALE_COLORS['light_gray']# '#bdc3c7'
```

## Best Practices

### 1. Choose the Right Backend

- **Matplotlib**: Best for static exports (PDF, PNG) and publications
- **Bokeh**: Best for interactive exploration and web dashboards
- **Plotly**: Best for sharing interactive charts

### 2. Use Appropriate Chart Types

- **Equity Curve**: Show overall performance over time
- **Drawdown**: Highlight risk and recovery periods
- **Monthly Heatmap**: Understand seasonal patterns
- **Distribution**: Analyze return characteristics
- **Trade Scatter**: Identify trade patterns

### 3. Optimize for Your Audience

- **Publications**: Use minimal theme, high DPI, vector formats (SVG, PDF)
- **Presentations**: Use dark theme, larger fonts, PNG format
- **Interactive Analysis**: Use Bokeh with linked crosshairs
- **Reports**: Use HTML reports with embedded charts

### 4. Performance Optimization

```python
# For large datasets, use downsampling
fig = plot(
    results,
    downsample=True,
    downsample_points=5000
)

# For batch processing, suppress display
fig = plot(results, show=False)
save_figure(fig, 'output.png')
plt.close(fig)
```

### 5. Customization

```python
# Customize individual plots
fig = plot(
    results,
    plot_equity=True,
    plot_drawdown=True,
    equity_color='#3498db',
    drawdown_color='#e74c3c',
    show_grid=True,
    grid_alpha=0.3,
    title='My Strategy Performance',
    watermark='Confidential'
)
```

## Troubleshooting

### Issue: Bokeh Not Available

```python
# Check if Bokeh is installed
from apps.plotting import BOKEH_AVAILABLE

if not BOKEH_AVAILABLE:
    # Install Bokeh
    # pip install bokeh
    print("Bokeh not available, using matplotlib")
```

### Issue: Font Issues

```python
# Set custom font
from apps.plotting import set_custom_font

set_custom_font('Arial', fallback='sans-serif')
```

### Issue: Memory Issues with Large Datasets

```python
# Use downsampling
fig = plot(results, downsample=True, downsample_points=10000)

# Or plot specific time ranges
fig = plot(
    results,
    start_date='2024-01-01',
    end_date='2024-12-31'
)
```

### Issue: Figure Not Showing

```python
# Explicitly show figure
import matplotlib.pyplot as plt
fig = plot(results)
plt.show()

# Or use output handling
from apps.plotting import handle_plot_output
handle_plot_output(fig, show=True)
```

## API Reference

### Main Functions

- `plot()` - Primary plotting function for backtest results
- `plot_all()` - Generate all available plots
- `create_html_report()` - Create comprehensive HTML report

### Chart Functions

- `_plot_ohlc_matplotlib()` - OHLC chart (Matplotlib)
- `_plot_ohlc_bokeh()` - OHLC chart (Bokeh)
- `_plot_equity_curve()` - Equity curve
- `_plot_drawdown()` - Drawdown chart
- `_plot_monthly_heatmap()` - Monthly returns heatmap
- `_plot_distribution()` - Returns distribution
- `_plot_trade_scatter()` - Trade scatter plot

### Theme Functions

- `set_theme()` - Set active theme
- `get_current_theme()` - Get active theme name
- `list_themes()` - List available themes
- `create_custom_theme()` - Create custom theme
- `theme_context()` - Temporary theme context

### Output Functions

- `save_figure()` - Save figure to file
- `save_multiple_formats()` - Save in multiple formats
- `open_in_browser()` - Open HTML in browser
- `handle_plot_output()` - Automatic output handling

### Interactive Functions (Bokeh)

- `add_ohlc_hover()` - Add OHLC hover tooltip
- `add_linked_crosshair()` - Link crosshairs across plots
- `add_range_selector()` - Add range selector
- `sync_zoom_across_figures()` - Sync zoom across figures

### Utility Functions

- `initialize_plotting()` - Initialize plotting system
- `configure_matplotlib()` - Configure Matplotlib
- `configure_bokeh()` - Configure Bokeh
- `_get_colors()` - Get color scheme
- `_format_axis()` - Format axis
- `_format_grid()` - Format grid

## Examples

See the `examples/backtest/plotting/` directory for comprehensive examples:

- `plot_example.py` - Basic plotting examples
- `charts_example.py` - Price charts
- `performance_example.py` - Performance metrics
- `drawdown_example.py` - Drawdown analysis
- `example_interactive_bokeh.py` - Interactive Bokeh features
- `example_themes.py` - Theme customization
- `example_batch_plotting.py` - Batch plotting
- `example_plotly_conversion.py` - Plotly conversion

## See Also

- [Backtest Module Documentation](../README.md)
- [Statistics Module Documentation](../stats/README.md)
- [Examples Directory](../../../examples/backtest/plotting/)
- [Implementation Plan](../../../docs/Implementation_Plan.md)

## Contributing

When adding new plotting functions:

1. Follow the existing code structure
2. Add comprehensive docstrings with examples
3. Support both Matplotlib and Bokeh (where applicable)
4. Include type hints
5. Add unit tests
6. Update this documentation
7. Add examples to the examples directory

## License

This module is part of the HaruQuant trading system.
