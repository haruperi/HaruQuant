import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import matplotlib.pyplot as plt
from apps.plotting.core import (
    _get_colors,
    configure_matplotlib,
    configure_seaborn,
    PercentageFormatter,
    CurrencyFormatter,
    CompactNumberFormatter,
    _format_axis,
    _format_grid,
    _format_legend,
    _format_date_axis,
    _get_backend,
    _backend_context,
    _create_figure,
    _cleanup_figure,
    save_figure,
    initialize_plotting
)

class TestColors:
    def test_get_colors_color(self):
        """Test getting color palette."""
        colors = _get_colors(mode="color")
        assert "profit" in colors
        assert colors["profit"] == "#2ecc71"

    def test_get_colors_grayscale(self):
        """Test getting grayscale palette."""
        colors = _get_colors(mode="grayscale")
        assert "profit" in colors
        assert colors["profit"] == "#2d2d2d"

class TestConfiguration:
    def test_configure_matplotlib(self):
        """Test matplotlib configuration."""
        configure_matplotlib(dpi=150, figsize=(10, 6))
        assert plt.rcParams["figure.dpi"] == 150
        assert plt.rcParams["figure.figsize"] == [10.0, 6.0]

    def test_configure_seaborn(self):
        """Test seaborn configuration."""
        with patch("seaborn.set_context") as mock_context:
            with patch("seaborn.set_palette") as mock_palette:
                configure_seaborn(context="poster", palette="muted")
                mock_context.assert_called_with("poster")
                mock_palette.assert_called_with("muted")

    def test_initialize_plotting(self):
        """Test initialization of all plotting libs."""
        with patch("apps.plotting.core.configure_matplotlib") as mock_mpl:
            with patch("apps.plotting.core.configure_seaborn") as mock_sns:
                with patch("apps.plotting.core.configure_bokeh") as mock_bokeh:
                    with patch("apps.plotting.core.BOKEH_AVAILABLE", True):
                        initialize_plotting()
                        mock_mpl.assert_called()
                        mock_sns.assert_called()
                        mock_bokeh.assert_called()

class TestFormatters:
    def test_percentage_formatter(self):
        """Test percentage formatting."""
        fmt = PercentageFormatter()
        assert fmt(0.1) == "10.0%"
        assert fmt(0.5555, None) == "55.5%"

    def test_currency_formatter(self):
        """Test currency formatting."""
        fmt = CurrencyFormatter()
        assert fmt(100) == "$100"
        assert fmt(1500) == "$1.5K"
        assert fmt(2000000) == "$2.0M"

    def test_compact_number_formatter(self):
        """Test compact number formatting."""
        fmt = CompactNumberFormatter()
        assert fmt(100) == "100"
        assert fmt(1500) == "1.5K"
        assert fmt(2000000) == "2.0M"
        assert fmt(3000000000) == "3.0B"

class TestFormatUtilities:
    def test_format_axis(self):
        """Test axis formatting."""
        fig, ax = plt.subplots()
        _format_axis(ax, title="Test", xlabel="X", ylabel="Y")
        assert ax.get_title() == "Test"
        assert ax.get_xlabel() == "X"
        assert ax.get_ylabel() == "Y"
        plt.close(fig)

    def test_format_date_axis(self):
        """Test date axis formatting."""
        fig, ax = plt.subplots()
        dates = pd.date_range("2024-01-01", periods=10)
        _format_date_axis(ax, dates)
        assert ax.xaxis.get_major_formatter() is not None
        plt.close(fig)

class TestBackendHelpers:
    def test_get_backend(self):
        """Test backend detection."""
        backend = _get_backend()
        assert isinstance(backend, str)

    def test_backend_context(self):
        """Test backend context manager."""
        with _backend_context("Agg"):
            assert plt.get_backend() == "Agg"

class TestFigureHelpers:
    def test_create_and_cleanup_figure(self):
        """Test figure creation and cleanup."""
        fig, ax = _create_figure()
        assert isinstance(fig, plt.Figure)
        _cleanup_figure(fig)

    def test_save_figure(self, tmp_path):
        """Test saving figure."""
        fig, ax = plt.subplots()
        output_path = tmp_path / "test_plot"
        
        saved_files = save_figure(fig, output_path, formats=["png"])
        
        assert len(saved_files) == 1
        assert saved_files[0].exists()
        assert saved_files[0].suffix == ".png"
        
        plt.close(fig)
