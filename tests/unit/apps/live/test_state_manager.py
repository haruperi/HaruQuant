
import json
import threading
import time
from datetime import date, datetime
import pytest
from apps.live.state_manager import StateManager

def test_initialization_defaults(tmp_path):
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    summary = manager.get_state_summary()
    assert summary["enabled"] is True
    assert summary["paused"] is False
    assert summary["trade_count_today"] == 0
    assert summary["last_reset_date"] == str(date.today())
    # state_file might not exist until first save

def test_load_existing_state(tmp_path):
    state_file = tmp_path / "state.json"
    initial_state = {
        "enabled": False,
        "paused": True,
        "trade_count_today": 5,
        "last_reset_date": str(date.today()),
        "last_run": "2023-01-01T12:00:00"
    }
    state_file.write_text(json.dumps(initial_state))
    
    manager = StateManager(str(state_file))
    summary = manager.get_state_summary()
    
    assert summary["enabled"] is False
    assert summary["paused"] is True
    assert summary["trade_count_today"] == 5

def test_pause_resume_enable_disable(tmp_path):
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    manager.pause()
    assert manager.is_paused() is True
    
    manager.resume()
    assert manager.is_paused() is False
    
    manager.disable()
    assert manager.is_enabled() is False
    
    manager.enable()
    assert manager.is_enabled() is True
    assert manager.is_paused() is False  # Enable should unpause

def test_trade_counter(tmp_path):
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    assert manager.get_trade_count_today() == 0
    
    count = manager.increment_trade_count()
    assert count == 1
    assert manager.get_trade_count_today() == 1
    
    manager.increment_trade_count()
    assert manager.get_trade_count_today() == 2
    
    manager.reset_daily_counter()
    assert manager.get_trade_count_today() == 0

def test_daily_reset_logic(tmp_path):
    state_file = tmp_path / "state.json"
    yesterday = "2023-01-01"
    initial_state = {
        "trade_count_today": 10,
        "last_reset_date": yesterday
    }
    state_file.write_text(json.dumps(initial_state))
    
    manager = StateManager(str(state_file))
    
    # access should trigger reset because date changed
    assert manager.get_trade_count_today() == 0
    
    summary = manager.get_state_summary()
    assert summary["last_reset_date"] == str(date.today())

def test_last_run_update(tmp_path):
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    assert manager.get_last_run() is None
    
    dt = datetime(2023, 1, 1, 12, 0, 0)
    manager.update_last_run(dt)
    
    assert manager.get_last_run() == dt
    
    # Test default (now)
    manager.update_last_run()
    assert manager.get_last_run().date() == date.today()

def test_thread_safety(tmp_path):
    state_file = tmp_path / "state.json"
    manager = StateManager(str(state_file))
    
    def worker():
        for _ in range(100):
            manager.increment_trade_count()
            
    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
        
    assert manager.get_trade_count_today() == 500
