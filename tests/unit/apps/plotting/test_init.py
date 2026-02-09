import pytest
import apps.plotting

def test_plotting_exports():
    """Test that all expected symbols are exported in __init__.py."""
    expected_exports = [
        "plot",
        "plot_all",
        "create_html_report",
        "to_plotly",
        "save_plotly_html",
        "convert_and_save",
        "save_multiple_formats",
        "set_theme",
        "get_current_theme",
        "plot_snapshot",
        "plot_returns",
        "plot_drawdown",
        "plot_monthly_heatmap",
        "initialize_plotting",
    ]
    
    for symbol in expected_exports:
        assert hasattr(apps.plotting, symbol), f"{symbol} not exported"

def test_module_metadata():
    """Test module metadata."""
    assert hasattr(apps.plotting, "__version__")
    assert hasattr(apps.plotting, "__author__")
