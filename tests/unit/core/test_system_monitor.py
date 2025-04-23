"""
Tests for system health monitoring module.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.core.system_monitor import (
    SystemMonitor,
    SystemStatus,
    SystemMetrics
)

@pytest.fixture
def system_monitor():
    """Create a system monitor instance for testing."""
    return SystemMonitor(update_interval=0.1)

@pytest.mark.asyncio
async def test_system_monitor_start_stop(system_monitor):
    """Test starting and stopping the system monitor."""
    # Test starting
    await system_monitor.start()
    assert system_monitor._monitor_task is not None
    assert not system_monitor._stop_event.is_set()
    
    # Test stopping
    await system_monitor.stop()
    assert system_monitor._monitor_task is None
    assert system_monitor._stop_event.is_set()

@pytest.mark.asyncio
async def test_system_monitor_double_start(system_monitor):
    """Test starting the monitor when it's already running."""
    await system_monitor.start()
    initial_task = system_monitor._monitor_task
    
    # Try starting again
    await system_monitor.start()
    assert system_monitor._monitor_task == initial_task  # Should not create new task
    
    await system_monitor.stop()

@pytest.mark.asyncio
async def test_system_monitor_double_stop(system_monitor):
    """Test stopping the monitor when it's not running."""
    # Try stopping when not started
    await system_monitor.stop()
    
    # Start and stop normally
    await system_monitor.start()
    await system_monitor.stop()
    
    # Try stopping again
    await system_monitor.stop()

@pytest.mark.asyncio
async def test_collect_metrics(system_monitor):
    """Test metric collection."""
    with patch('psutil.cpu_percent', return_value=50.0), \
         patch('psutil.virtual_memory', return_value=MagicMock(percent=60.0)), \
         patch('psutil.disk_usage', return_value=MagicMock(percent=70.0)), \
         patch('psutil.net_io_counters', return_value=MagicMock(
             bytes_sent=1000,
             bytes_recv=2000
         )):
        
        metrics = await system_monitor._collect_metrics()
        
        assert isinstance(metrics, SystemMetrics)
        assert metrics.cpu_percent == 50.0
        assert metrics.memory_percent == 60.0
        assert metrics.disk_percent == 70.0
        assert metrics.network_io['bytes_sent'] == 1000
        assert metrics.network_io['bytes_recv'] == 2000
        assert isinstance(metrics.timestamp, datetime)

def test_determine_status(system_monitor):
    """Test status determination based on thresholds."""
    # Test healthy status
    status = system_monitor._determine_status(50.0, 50.0, 50.0)
    assert status == SystemStatus.HEALTHY
    
    # Test warning status
    status = system_monitor._determine_status(85.0, 50.0, 50.0)
    assert status == SystemStatus.WARNING
    
    # Test critical status
    status = system_monitor._determine_status(95.0, 50.0, 50.0)
    assert status == SystemStatus.CRITICAL

@pytest.mark.asyncio
async def test_check_thresholds(system_monitor):
    """Test threshold checking and alert generation."""
    metrics = SystemMetrics(
        timestamp=datetime.now(),
        cpu_percent=95.0,
        memory_percent=50.0,
        disk_percent=50.0,
        network_io={'bytes_sent': 0, 'bytes_recv': 0},
        status=SystemStatus.CRITICAL,
        trading_system_status="OK",
        mt5_connection_status="Connected",
        performance_metrics={}
    )
    
    with patch.object(system_monitor, '_check_thresholds') as mock_check:
        await system_monitor._check_thresholds(metrics)
        mock_check.assert_called_once_with(metrics)

def test_get_current_metrics(system_monitor):
    """Test getting current metrics."""
    # Test when no metrics available
    assert system_monitor.get_current_metrics() is None
    
    # Add some test metrics
    test_metrics = SystemMetrics(
        timestamp=datetime.now(),
        cpu_percent=50.0,
        memory_percent=50.0,
        disk_percent=50.0,
        network_io={'bytes_sent': 0, 'bytes_recv': 0},
        status=SystemStatus.HEALTHY,
        trading_system_status="OK",
        mt5_connection_status="Connected",
        performance_metrics={}
    )
    system_monitor.metrics_history[test_metrics.timestamp] = test_metrics
    
    # Test getting current metrics
    current_metrics = system_monitor.get_current_metrics()
    assert current_metrics == test_metrics

def test_get_metrics_history(system_monitor):
    """Test getting metrics history."""
    # Add test metrics
    now = datetime.now()
    metrics1 = SystemMetrics(
        timestamp=now - timedelta(minutes=2),
        cpu_percent=50.0,
        memory_percent=50.0,
        disk_percent=50.0,
        network_io={'bytes_sent': 0, 'bytes_recv': 0},
        status=SystemStatus.HEALTHY,
        trading_system_status="OK",
        mt5_connection_status="Connected",
        performance_metrics={}
    )
    metrics2 = SystemMetrics(
        timestamp=now - timedelta(minutes=1),
        cpu_percent=60.0,
        memory_percent=60.0,
        disk_percent=60.0,
        network_io={'bytes_sent': 0, 'bytes_recv': 0},
        status=SystemStatus.HEALTHY,
        trading_system_status="OK",
        mt5_connection_status="Connected",
        performance_metrics={}
    )
    system_monitor.metrics_history[metrics1.timestamp] = metrics1
    system_monitor.metrics_history[metrics2.timestamp] = metrics2
    
    # Test getting full history
    history = system_monitor.get_metrics_history()
    assert len(history) == 2
    
    # Test getting history with time range
    start_time = now - timedelta(minutes=1, seconds=30)
    end_time = now
    history = system_monitor.get_metrics_history(start_time, end_time)
    assert len(history) == 1
    assert list(history.values())[0] == metrics2

def test_get_system_status(system_monitor):
    """Test getting system status."""
    # Test when no metrics available
    assert system_monitor.get_system_status() == SystemStatus.HEALTHY
    
    # Add test metrics
    test_metrics = SystemMetrics(
        timestamp=datetime.now(),
        cpu_percent=50.0,
        memory_percent=50.0,
        disk_percent=50.0,
        network_io={'bytes_sent': 0, 'bytes_recv': 0},
        status=SystemStatus.WARNING,
        trading_system_status="OK",
        mt5_connection_status="Connected",
        performance_metrics={}
    )
    system_monitor.metrics_history[test_metrics.timestamp] = test_metrics
    
    # Test getting status
    assert system_monitor.get_system_status() == SystemStatus.WARNING 