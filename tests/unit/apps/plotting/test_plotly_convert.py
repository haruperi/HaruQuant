import pytest
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from unittest.mock import MagicMock, patch
from apps.plotting.plotly_convert import (
    to_plotly,
    save_plotly_html,
    create_plotly_time_series,
    create_plotly_candlestick,
    convert_and_save
)

@pytest.fixture
def mock_plotly_available():
    with patch("apps.plotting.plotly_convert.PLOTLY_AVAILABLE", True):
        yield

@pytest.fixture
def mock_go_figure():
    with patch("apps.plotting.plotly_convert.go.Figure") as mock_fig:
        mock_instance = MagicMock()
        mock_fig.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def sample_mpl_figure():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 9], label="line1", color="blue", linestyle="--")
    ax.scatter([1, 2, 3], [2, 5, 8], label="points", color="red")
    ax.bar([1, 2, 3], [1, 2, 3], label="bars") # Should trigger patch logic
    ax.set_title("Test Plot")
    ax.set_xlabel("X-Axis")
    ax.set_ylabel("Y-Axis")
    return fig

class TestPlotlyConvert:
    def test_to_plotly_conversion(self, mock_plotly_available, sample_mpl_figure):
        with patch("apps.plotting.plotly_convert.go.Scatter") as mock_scatter:
            with patch("apps.plotting.plotly_convert.go.Figure") as mock_fig_cls:
                plotly_fig = to_plotly(sample_mpl_figure)
                assert plotly_fig is not None
                # Check that traces were added (lines and scatter)
                # Scatter is used for both lines and markers in plotly
                assert mock_scatter.call_count >= 1

    def test_to_plotly_missing_backend(self):
        with patch("apps.plotting.plotly_convert.PLOTLY_AVAILABLE", False):
            with pytest.raises(ImportError, match="Plotly is not installed"):
                to_plotly(plt.figure())

    def test_save_plotly_html(self, mock_plotly_available, mock_go_figure, tmp_path):
        output_path = tmp_path / "chart.html"
        save_plotly_html(mock_go_figure, str(output_path))
        mock_go_figure.write_html.assert_called()

    def test_convert_and_save(self, mock_plotly_available, sample_mpl_figure, tmp_path):
        output_path = tmp_path / "converted.html"
        with patch("apps.plotting.plotly_convert.to_plotly") as mock_to_plotly:
            with patch("apps.plotting.plotly_convert.save_plotly_html") as mock_save:
                convert_and_save(sample_mpl_figure, str(output_path))
                mock_to_plotly.assert_called()
                mock_save.assert_called()

class TestPlotlyCreators:
    def test_create_plotly_time_series(self, mock_plotly_available):
        df = pd.DataFrame({'date': pd.date_range('2024-01-01', periods=10), 'value': range(10)})
        with patch("apps.plotting.plotly_convert.go.Figure") as mock_fig_cls:
            fig = create_plotly_time_series(df, 'value', 'date')
            assert fig is not None

    def test_create_plotly_candlestick(self, mock_plotly_available):
        df = pd.DataFrame({
            'open': [100]*5, 'high': [110]*5, 'low': [90]*5, 'close': [105]*5, 'volume': [1000]*5
        }, index=pd.date_range('2024-01-01', periods=5))
        
        with patch("apps.plotting.plotly_convert.go.Figure") as mock_fig_cls:
            # Test without volume first
            fig = create_plotly_candlestick(df, volume_col=None)
            assert fig is not None

        # Test with volume (requires make_subplots)
        with patch("apps.plotting.plotly_convert.make_subplots") as mock_subplots:
             create_plotly_candlestick(df, volume_col='volume')
             mock_subplots.assert_called()
