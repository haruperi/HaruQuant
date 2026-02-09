import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from apps.plotting.output import (
    save_figure,
    sanitize_filename,
    generate_filename,
    should_return_figure,
    handle_plot_output,
    open_in_browser,
    save_multiple_formats
)

@pytest.fixture
def temp_output_dir(tmp_path):
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir

@pytest.fixture
def sample_fig():
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot([1, 2, 3], [1, 2, 3])
    return fig

class TestFilenameUtilities:
    def test_sanitize_filename(self):
        assert sanitize_filename("test/file:name") == "test_file_name"
        assert sanitize_filename("  test  ") == "test"
        assert sanitize_filename("a__b") == "a_b"

    def test_generate_filename(self):
        name = generate_filename("MyStrategy", "equity")
        assert name == "MyStrategy_equity.png"
        
        name_ts = generate_filename("Strat", "stats", add_timestamp=True)
        assert len(name_ts.split("_")) >= 3

class TestSaveFigure:
    def test_save_matplotlib_figure(self, sample_fig, temp_output_dir):
        filepath = temp_output_dir / "test.png"
        result = save_figure(sample_fig, filepath)
        assert result.exists()
        assert result.name == "test.png"

    def test_save_figure_creates_dirs(self, sample_fig, temp_output_dir):
        filepath = temp_output_dir / "nested" / "test.pdf"
        result = save_figure(sample_fig, filepath)
        assert result.exists()
        assert result.parent.exists()

    def test_save_figure_overwrite_protection(self, sample_fig, temp_output_dir):
        filepath = temp_output_dir / "test.png"
        save_figure(sample_fig, filepath)
        
        with pytest.raises(FileExistsError):
            save_figure(sample_fig, filepath, overwrite=False)

    def test_save_multiple_formats(self, sample_fig, temp_output_dir):
        base_path = temp_output_dir / "chart"
        paths = save_multiple_formats(sample_fig, base_path, ["png", "svg"])
        
        assert "png" in paths
        assert "svg" in paths
        assert paths["png"].exists()
        assert paths["svg"].exists()

class TestBrowserIntegration:
    @patch("apps.plotting.output.webbrowser")
    def test_open_in_browser(self, mock_browser, temp_output_dir):
        html_file = temp_output_dir / "test.html"
        html_file.touch()
        
        assert open_in_browser(html_file) is True
        mock_browser.get.return_value.open.assert_called()

    def test_open_missing_file(self):
        assert open_in_browser("nonexistent.html") is False

class TestOutputLogic:
    def test_should_return_figure(self):
        assert should_return_figure(show=False, save=False) is True
        assert should_return_figure(return_fig=True) is True
        assert should_return_figure(show=True, save=True) is False

    @patch("matplotlib.pyplot.show")
    def test_handle_plot_output_show(self, mock_show, sample_fig):
        handle_plot_output(sample_fig, show=True, save=False)
        mock_show.assert_called()

    def test_handle_plot_output_save(self, sample_fig, temp_output_dir):
        filepath = temp_output_dir / "saved.png"
        handle_plot_output(sample_fig, show=False, save=True, filepath=filepath)
        assert filepath.exists()

    def test_handle_plot_output_return(self, sample_fig):
        res = handle_plot_output(sample_fig, show=False, save=False, return_fig=True)
        assert res == sample_fig
