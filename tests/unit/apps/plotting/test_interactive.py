import pytest
import numpy as np
import matplotlib
matplotlib.use('Agg')
from unittest.mock import MagicMock, patch
from apps.plotting.interactive import (
    add_linked_crosshair,
    add_pan_zoom_tools,
    sync_zoom_across_figures,
    add_ohlc_hover,
    add_equity_hover,
    add_indicator_hover,
    add_trade_hover,
    add_drawdown_hover,
    customize_hover_css,
    configure_interactive_legend,
    create_legend_toggles,
    add_range_selector,
    create_range_selector_layout,
    apply_standard_tools,
    create_linked_chart_layout
)

@pytest.fixture
def mock_bokeh_available():
    with patch("apps.plotting.interactive.BOKEH_AVAILABLE", True):
        yield

@pytest.fixture
def mock_figure():
    fig = MagicMock()
    fig.add_tools = MagicMock()
    fig.toolbar.active_drag = None
    fig.toolbar.active_scroll = None
    fig.x_range = MagicMock()
    fig.y_range = MagicMock()
    return fig

class TestInteractiveTools:
    def test_add_linked_crosshair_no_bokeh(self, mock_figure):
        with patch("apps.plotting.interactive.BOKEH_AVAILABLE", False):
            add_linked_crosshair([mock_figure])
            mock_figure.add_tools.assert_not_called()

    def test_add_linked_crosshair(self, mock_bokeh_available, mock_figure):
        with patch("apps.plotting.interactive.CrosshairTool") as mock_tool:
            add_linked_crosshair([mock_figure])
            mock_tool.assert_called()
            mock_figure.add_tools.assert_called()

    def test_add_pan_zoom_tools(self, mock_bokeh_available, mock_figure):
        with patch("apps.plotting.interactive.PanTool"), \
             patch("apps.plotting.interactive.WheelZoomTool"), \
             patch("apps.plotting.interactive.BoxZoomTool"), \
             patch("apps.plotting.interactive.ResetTool"):
            
            add_pan_zoom_tools(mock_figure)
            assert mock_figure.add_tools.called

    def test_sync_zoom_across_figures(self, mock_bokeh_available):
        fig1 = MagicMock()
        fig2 = MagicMock()
        fig1.x_range = "range1"
        fig2.x_range = "range2"
        
        sync_zoom_across_figures([fig1, fig2], sync_x=True)
        assert fig2.x_range == fig1.x_range

class TestHoverTools:
    def test_add_ohlc_hover(self, mock_bokeh_available, mock_figure):
        with patch("apps.plotting.interactive.HoverTool") as mock_hover:
            add_ohlc_hover(mock_figure)
            mock_hover.assert_called()
            mock_figure.add_tools.assert_called()

    def test_add_equity_hover(self, mock_bokeh_available, mock_figure):
        with patch("apps.plotting.interactive.HoverTool") as mock_hover:
            add_equity_hover(mock_figure)
            mock_hover.assert_called()

    def test_customize_hover_css(self):
        css = customize_hover_css()
        assert "background-color" in css
        assert ".bk-tooltip" in css

class TestLegendTools:
    def test_configure_interactive_legend(self, mock_bokeh_available):
        fig = MagicMock()
        fig.legend = MagicMock()
        
        configure_interactive_legend(fig)
        assert fig.legend.click_policy == "hide"

    def test_create_legend_toggles(self, mock_bokeh_available):
        with patch("apps.plotting.interactive.CheckboxGroup") as mock_cb:
            create_legend_toggles(["A", "B"])
            mock_cb.assert_called()

class TestRangeSelector:
    def test_add_range_selector(self, mock_bokeh_available, mock_figure):
        with patch("apps.plotting.interactive.figure") as mock_fig_cls:
            with patch("apps.plotting.interactive.RangeTool"):
                mock_source = MagicMock()
                fig, tool = add_range_selector(mock_figure, mock_source)
                assert fig is not None

class TestLayouts:
    def test_apply_standard_tools(self, mock_bokeh_available, mock_figure):
        with patch("apps.plotting.interactive.add_pan_zoom_tools") as mock_pz:
            apply_standard_tools(mock_figure)
            mock_pz.assert_called()

    def test_create_linked_chart_layout(self, mock_bokeh_available):
        figs = [MagicMock(), MagicMock()]
        with patch("apps.plotting.interactive.column") as mock_col:
            create_linked_chart_layout(figs, layout_type="column")
            mock_col.assert_called()
