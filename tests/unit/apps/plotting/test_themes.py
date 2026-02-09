import pytest
import shutil
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from apps.plotting.themes import (
    set_theme,
    get_current_theme,
    reset_theme,
    list_themes,
    ThemeContext,
    apply_theme_to_figure,
    create_custom_theme,
    set_color_palette,
    set_custom_font,
    add_watermark,
    add_logo,
    save_theme_preference,
    load_theme_preference,
    THEMES,
    LIGHT_THEME
)

@pytest.fixture
def temp_config_dir(tmp_path):
    config_dir = tmp_path / ".haruquant"
    config_dir.mkdir()
    return config_dir

class TestThemeManagement:
    def setup_method(self):
        reset_theme()

    def teardown_method(self):
        reset_theme()

    def test_set_theme(self):
        set_theme("dark")
        current = get_current_theme()
        assert current["name"] == "dark"
        assert plt.rcParams["figure.facecolor"] == current["matplotlib"]["figure.facecolor"]

    def test_set_invalid_theme(self):
        with pytest.raises(ValueError, match="Unknown theme"):
            set_theme("invalid_theme_name")

    def test_reset_theme(self):
        set_theme("dark")
        reset_theme()
        assert get_current_theme()["name"] == "light"

    def test_list_themes(self):
        themes = list_themes()
        assert "light" in themes
        assert "dark" in themes

    def test_theme_context(self):
        initial_theme = get_current_theme()["name"]
        with ThemeContext("dark"):
            assert get_current_theme()["name"] == "dark"
        assert get_current_theme()["name"] == initial_theme

class TestThemeApplication:
    def test_apply_theme_to_figure(self):
        fig, ax = plt.subplots()
        set_theme("light")
        apply_theme_to_figure(fig, "dark")
        # Check if figure background color matches dark theme
        assert fig.patch.get_facecolor() == (30/255, 30/255, 30/255, 1.0) # #1e1e1e matches dark theme
        plt.close(fig)

    def test_create_custom_theme(self):
        custom = create_custom_theme(
            "my_theme", 
            base_theme="light",
            color_overrides={"profit": "#123456"}
        )
        assert custom["name"] == "my_theme"
        assert custom["colors"]["profit"] == "#123456"

    def test_set_color_palette(self):
        new_colors = ["#ff0000", "#00ff00"]
        set_color_palette(new_colors)
        assert get_current_theme()["line_colors"] == new_colors

    def test_set_custom_font(self):
        set_custom_font("Arial", 12, "bold")
        assert plt.rcParams["font.family"] == ["Arial"]
        assert plt.rcParams["font.size"] == 12.0
        assert plt.rcParams["font.weight"] == "bold"

class TestDecorations:
    def test_add_watermark(self):
        fig = plt.figure()
        add_watermark(fig, "TEST", alpha=0.5)
        # Check if text was added
        assert len(fig.texts) > 0
        plt.close(fig)

    @patch("matplotlib.pyplot.imread")
    def test_add_logo(self, mock_imread, tmp_path):
        fig = plt.figure()
        logo_path = tmp_path / "logo.png"
        logo_path.touch()
        
        # Mock image data
        mock_imread.return_value = [[0,0],[0,0]] # Dummy image data
        
        add_logo(fig, logo_path)
        assert len(fig.artists) > 0
        plt.close(fig)

class TestPersistence:
    @patch("apps.plotting.themes.get_theme_config_path")
    def test_save_and_load_preference(self, mock_path, temp_config_dir):
        config_file = temp_config_dir / "plot_theme.json"
        mock_path.return_value = config_file

        save_theme_preference("dark")
        assert config_file.exists()
        
        loaded = load_theme_preference()
        assert loaded == "dark"

    @patch("apps.plotting.themes.get_theme_config_path")
    def test_load_missing_preference(self, mock_path, temp_config_dir):
        mock_path.return_value = temp_config_dir / "missing.json"
        assert load_theme_preference() is None
