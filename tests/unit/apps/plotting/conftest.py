import pytest
from unittest.mock import MagicMock, patch
import sys

@pytest.fixture(scope="session", autouse=True)
def mock_bokeh_modules():
    """Mock bokeh modules globally for the session."""
    sys.modules["bokeh"] = MagicMock()
    sys.modules["bokeh.plotting"] = MagicMock()
    sys.modules["bokeh.models"] = MagicMock()
    sys.modules["bokeh.layouts"] = MagicMock()
    sys.modules["bokeh.io"] = MagicMock()
    sys.modules["bokeh.palettes"] = MagicMock()
    sys.modules["bokeh.transform"] = MagicMock()

@pytest.fixture(autouse=True)
def inject_bokeh_objects(monkeypatch):
    """Inject mock Bokeh objects into modules that use them."""
    
    # Create mocks for common Bokeh objects
    mock_figure = MagicMock()
    mock_ColumnDataSource = MagicMock()
    mock_HoverTool = MagicMock()
    mock_Span = MagicMock()
    mock_Range1d = MagicMock()
    mock_LinearAxis = MagicMock()
    mock_CrosshairTool = MagicMock()
    mock_PanTool = MagicMock()
    mock_ResetTool = MagicMock()
    mock_WheelZoomTool = MagicMock()
    mock_NumeralTickFormatter = MagicMock()
    mock_DatetimeTickFormatter = MagicMock()
    mock_SaveTool = MagicMock()
    mock_BoxZoomTool = MagicMock()
    mock_DataRange1d = MagicMock()
    mock_LinearColorMapper = MagicMock()
    mock_ColorBar = MagicMock()
    mock_BasicTicker = MagicMock()
    mock_PrintfTickFormatter = MagicMock()
    mock_LayoutDOM = MagicMock()
    mock_gridplot = MagicMock()
    mock_row = MagicMock()
    mock_column = MagicMock()
    mock_curdoc = MagicMock()
    mock_Band = MagicMock()
    mock_RangeTool = MagicMock()
    mock_CheckboxGroup = MagicMock()
    mock_CustomJS = MagicMock()
    
    # List of modules that need patching
    modules_to_patch = [
        "apps.plotting.charts",
        "apps.plotting.interactive",
        "apps.plotting.markers",
        "apps.plotting.distribution",
        "apps.plotting.drawdown",
        "apps.plotting.heatmap",
        "apps.plotting.performance",
        "apps.plotting.main",
        "apps.plotting.batch",
    ]
    
    # Patch each module
    for module_name in modules_to_patch:
        try:
            # Import the module first to ensure it's loaded
            __import__(module_name)
            module = sys.modules[module_name]
            
            # Inject objects
            monkeypatch.setattr(module, "BOKEH_AVAILABLE", True, raising=False)
            monkeypatch.setattr(module, "bokeh_figure", mock_figure, raising=False)
            monkeypatch.setattr(module, "figure", mock_figure, raising=False)
            monkeypatch.setattr(module, "ColumnDataSource", mock_ColumnDataSource, raising=False)
            monkeypatch.setattr(module, "HoverTool", mock_HoverTool, raising=False)
            monkeypatch.setattr(module, "Span", mock_Span, raising=False)
            monkeypatch.setattr(module, "Range1d", mock_Range1d, raising=False)
            monkeypatch.setattr(module, "LinearAxis", mock_LinearAxis, raising=False)
            monkeypatch.setattr(module, "CrosshairTool", mock_CrosshairTool, raising=False)
            monkeypatch.setattr(module, "PanTool", mock_PanTool, raising=False)
            monkeypatch.setattr(module, "ResetTool", mock_ResetTool, raising=False)
            monkeypatch.setattr(module, "WheelZoomTool", mock_WheelZoomTool, raising=False)
            monkeypatch.setattr(module, "NumeralTickFormatter", mock_NumeralTickFormatter, raising=False)
            monkeypatch.setattr(module, "DatetimeTickFormatter", mock_DatetimeTickFormatter, raising=False)
            monkeypatch.setattr(module, "SaveTool", mock_SaveTool, raising=False)
            monkeypatch.setattr(module, "BoxZoomTool", mock_BoxZoomTool, raising=False)
            monkeypatch.setattr(module, "DataRange1d", mock_DataRange1d, raising=False)
            monkeypatch.setattr(module, "LinearColorMapper", mock_LinearColorMapper, raising=False)
            monkeypatch.setattr(module, "ColorBar", mock_ColorBar, raising=False)
            monkeypatch.setattr(module, "BasicTicker", mock_BasicTicker, raising=False)
            monkeypatch.setattr(module, "PrintfTickFormatter", mock_PrintfTickFormatter, raising=False)
            monkeypatch.setattr(module, "LayoutDOM", mock_LayoutDOM, raising=False)
            monkeypatch.setattr(module, "gridplot", mock_gridplot, raising=False)
            monkeypatch.setattr(module, "row", mock_row, raising=False)
            monkeypatch.setattr(module, "column", mock_column, raising=False)
            monkeypatch.setattr(module, "curdoc", mock_curdoc, raising=False)
            monkeypatch.setattr(module, "Band", mock_Band, raising=False)
            monkeypatch.setattr(module, "RangeTool", mock_RangeTool, raising=False)
            monkeypatch.setattr(module, "CheckboxGroup", mock_CheckboxGroup, raising=False)
            monkeypatch.setattr(module, "CustomJS", mock_CustomJS, raising=False)
            
        except (ImportError, KeyError):
            pass # Module might not be importable or loaded yet
