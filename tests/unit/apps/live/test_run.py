
from unittest.mock import Mock, patch, MagicMock
import pytest
import sys
import signal
from apps.live.run import main, setup_engine, validate_config_path

def test_validate_config_path_success(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.touch()
    assert validate_config_path(str(config_file)) is True

def test_validate_config_path_toml_success(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.touch()
    assert validate_config_path(str(config_file)) is True

def test_validate_config_path_missing():
    assert validate_config_path("non_existent.json") is False

def test_validate_config_path_not_file(tmp_path):
    assert validate_config_path(str(tmp_path)) is False

def test_setup_engine_success():
    with patch("apps.live.run.MultiStrategyEngine") as MockEngine:
        MockEngine.return_value.initialize.return_value = True
        
        engine = setup_engine("config.json")
        assert engine is not None
        MockEngine.assert_called_with("config.json")
        engine.initialize.assert_called()

def test_setup_engine_init_fail():
    with patch("apps.live.run.MultiStrategyEngine") as MockEngine:
        MockEngine.return_value.initialize.return_value = False
        
        engine = setup_engine("config.json")
        assert engine is None

def test_setup_engine_create_fail():
    with patch("apps.live.run.MultiStrategyEngine", side_effect=Exception("Fail")):
        engine = setup_engine("config.json")
        assert engine is None

def test_main_success(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.touch()
    
    with patch("apps.live.run.parse_arguments") as mock_args, \
         patch("apps.live.run.setup_engine") as mock_setup, \
         patch("apps.live.run.register_signal_handlers"), \
         patch("apps.live.run.print_startup_info"):
        
        mock_args.return_value = Mock(config=str(config_file))
        mock_engine = Mock()
        mock_setup.return_value = mock_engine
        
        ret = main()
        assert ret == 0
        mock_engine.run.assert_called()

def test_main_invalid_config():
    with patch("apps.live.run.parse_arguments") as mock_args, \
         patch("apps.live.run.validate_config_path", return_value=False):
        
        mock_args.return_value = Mock(config="invalid.json")
        ret = main()
        assert ret == 1

def test_main_setup_fail():
    with patch("apps.live.run.parse_arguments") as mock_args, \
         patch("apps.live.run.validate_config_path", return_value=True), \
         patch("apps.live.run.setup_engine", return_value=None):
        
        mock_args.return_value = Mock(config="config.json")
        ret = main()
        assert ret == 1

def test_main_run_exception():
    with patch("apps.live.run.parse_arguments") as mock_args, \
         patch("apps.live.run.validate_config_path", return_value=True), \
         patch("apps.live.run.setup_engine") as mock_setup, \
         patch("apps.live.run.register_signal_handlers"), \
         patch("apps.live.run.print_startup_info"):
        
        mock_args.return_value = Mock(config="config.json")
        mock_engine = Mock()
        mock_engine.run.side_effect = Exception("Crash")
        mock_setup.return_value = mock_engine
        
        ret = main()
        assert ret == 1
