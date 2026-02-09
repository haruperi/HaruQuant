import pytest
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from apps.plotting.batch import plot_all, create_html_report, _create_manifest, _embed_figure_html

@pytest.fixture
def mock_results():
    """Create mock backtest results."""
    dates = pd.date_range("2024-01-01", periods=100)
    equity = pd.Series(range(100, 200), index=dates)
    
    mock_res = MagicMock()
    mock_res.comprehensive_summary.return_value = {
        "Total Return": 10.5,
        "Sharpe Ratio": 1.5,
        "Max Drawdown": -5.0,
        "Win Rate": 60.0,
        "Number of Trades": 50,
        "Avg Trade": 0.5
    }
    mock_res._get_equity_series.return_value = equity
    mock_res.strategy_name = "TestStrategy"
    
    return mock_res

@pytest.fixture
def mock_results_dict():
    """Create mock results in dictionary format."""
    dates = pd.date_range("2024-01-01", periods=100)
    equity = pd.Series(range(100, 200), index=dates)
    
    broker = MagicMock()
    broker.equity = equity
    
    return {
        "stats": {
            "Total Return": 10.5,
            "Sharpe Ratio": 1.5,
        },
        "broker": broker,
        "strategy": "TestStrategy"
    }

class TestPlotAll:
    def test_plot_all_with_results_object(self, mock_results, tmp_path):
        """Test plot_all with BacktestResult object."""
        output_dir = tmp_path / "plots"
        
        with patch("apps.plotting.batch.save_figure") as mock_save:
            with patch("apps.plotting.batch.plot") as mock_plot:
                mock_save.return_value = [Path("test.png")]
                
                saved_plots = plot_all(
                    mock_results,
                    output_dir=output_dir,
                    prefix="test",
                    formats=["png"]
                )
                
                assert "main" in saved_plots
                assert "equity" in saved_plots
                assert "drawdown" in saved_plots

    def test_plot_all_with_dict(self, mock_results_dict, tmp_path):
        """Test plot_all with dictionary results."""
        output_dir = tmp_path / "plots"
        
        with patch("apps.plotting.batch.save_figure") as mock_save:
            with patch("apps.plotting.batch.plot") as mock_plot:
                mock_save.return_value = [Path("test.png")]
                
                saved_plots = plot_all(
                    mock_results_dict,
                    output_dir=output_dir,
                    prefix="test"
                )
                
                assert isinstance(saved_plots, dict)
                assert len(saved_plots) > 0

    def test_plot_all_error_handling(self, mock_results):
        """Test error handling in plot_all."""
        with patch("apps.plotting.batch.save_figure", side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                plot_all(mock_results)

class TestCreateHtmlReport:
    def test_create_html_report_basic(self, mock_results, tmp_path):
        """Test basic HTML report creation."""
        output_path = tmp_path / "report.html"
        
        with patch("apps.plotting.batch._embed_figure_html") as mock_embed:
            mock_embed.return_value = '<img src="test">'
            
            report_path = create_html_report(
                mock_results,
                output_path=output_path,
                title="Test Report"
            )
            
            assert report_path.exists()
            content = report_path.read_text(encoding="utf-8")
            assert "Test Report" in content
            assert "Performance Statistics" in content

    def test_create_html_report_plots_filtering(self, mock_results_dict, tmp_path):
        """Test filtering plots in HTML report."""
        output_path = tmp_path / "report.html"
        
        with patch("apps.plotting.batch._embed_figure_html") as mock_embed:
             with patch("matplotlib.pyplot.subplots") as mock_subplots:
                fig = MagicMock()
                ax = MagicMock()
                mock_subplots.return_value = (fig, ax)
                
                create_html_report(
                    mock_results_dict,
                    output_path=output_path,
                    include_plots=["equity", "drawdown"]
                )
                
                # Verify specific plots generated
                assert output_path.exists()

class TestEmbedFigure:
    def test_embed_figure_html(self):
        """Test embedding figure in HTML."""
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.plot([1, 2, 3], [1, 2, 3])
        
        html = _embed_figure_html(fig, alt_text="Test Plot")
        
        assert "<img" in html
        assert 'alt="Test Plot"' in html
        assert "data:image/png;base64" in html
        
        plt.close(fig)

class TestCreateManifest:
    def test_create_manifest(self, tmp_path):
        """Test manifest file creation."""
        saved_plots = {
            "main": [tmp_path / "main.png"],
            "equity": [tmp_path / "equity.png"]
        }
        
        _create_manifest(
            output_dir=tmp_path,
            saved_plots=saved_plots,
            prefix="test",
            formats=["png"]
        )
        
        manifest_path = tmp_path / "test_manifest.json"
        assert manifest_path.exists()
        import json
        data = json.loads(manifest_path.read_text())
        assert "plots" in data
        assert "main" in data["plots"]
