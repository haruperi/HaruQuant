
import pytest
from unittest.mock import MagicMock, patch
from apps.utils.scheduler import start_scheduler, shutdown_scheduler, _cleanup_old_simulation_sessions

@patch("apps.utils.scheduler._scheduler")
@patch("apps.utils.scheduler.logger")
def test_start_scheduler(mock_logger, mock_scheduler):
    # Test start when not running
    mock_scheduler.running = False
    start_scheduler()
    mock_scheduler.add_job.assert_called_once()
    mock_scheduler.start.assert_called_once()
    mock_logger.info.assert_called_with("Background scheduler started")
    
    # Test start when already running
    mock_scheduler.reset_mock()
    mock_logger.reset_mock()
    mock_scheduler.running = True
    start_scheduler()
    mock_scheduler.start.assert_not_called()

@patch("apps.utils.scheduler._scheduler")
@patch("apps.utils.scheduler.logger")
def test_shutdown_scheduler(mock_logger, mock_scheduler):
    # Test shutdown when running
    mock_scheduler.running = True
    shutdown_scheduler()
    mock_scheduler.shutdown.assert_called_once()
    mock_logger.info.assert_called_with("Background scheduler stopped")
    
    # Test shutdown when not running
    mock_scheduler.reset_mock()
    mock_scheduler.running = False
    shutdown_scheduler()
    mock_scheduler.shutdown.assert_not_called()

@patch("apps.utils.scheduler.DatabaseManager")
@patch("apps.utils.scheduler.logger")
def test_cleanup_old_simulation_sessions(mock_logger, mock_db_cls):
    mock_db = mock_db_cls.return_value
    
    # Case: items deleted
    mock_db.delete_simulation_sessions_older_than.return_value = 5
    _cleanup_old_simulation_sessions()
    mock_db.delete_simulation_sessions_older_than.assert_called_with(7)
    mock_logger.info.assert_called()
    
    # Case: no items deleted
    mock_logger.reset_mock()
    mock_db.delete_simulation_sessions_older_than.return_value = 0
    _cleanup_old_simulation_sessions()
    mock_logger.info.assert_not_called()
