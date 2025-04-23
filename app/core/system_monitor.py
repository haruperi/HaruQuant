"""
System health monitoring module for tracking system resources and trading system status.
"""

import asyncio
import psutil
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum, auto

from app.utils.logger import get_logger

logger = get_logger(__name__)

class SystemStatus(Enum):
    """System status enumeration."""
    HEALTHY = auto()
    WARNING = auto()
    CRITICAL = auto()

@dataclass
class SystemMetrics:
    """System metrics data class."""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, float]
    status: SystemStatus
    trading_system_status: str
    mt5_connection_status: str
    performance_metrics: Dict[str, float]

class SystemMonitor:
    """
    System health monitoring class for tracking system resources and trading system status.
    """
    
    def __init__(
        self,
        update_interval: float = 60.0,
        warning_thresholds: Optional[Dict[str, float]] = None,
        critical_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize the system monitor.
        
        Args:
            update_interval: Time between metric updates in seconds
            warning_thresholds: Warning thresholds for system metrics
            critical_thresholds: Critical thresholds for system metrics
        """
        self.update_interval = update_interval
        self.warning_thresholds = warning_thresholds or {
            'cpu_percent': 80.0,
            'memory_percent': 80.0,
            'disk_percent': 80.0
        }
        self.critical_thresholds = critical_thresholds or {
            'cpu_percent': 90.0,
            'memory_percent': 90.0,
            'disk_percent': 90.0
        }
        self.metrics_history: Dict[datetime, SystemMetrics] = {}
        self._stop_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """Start the system monitoring."""
        if self._monitor_task is not None:
            logger.warning("System monitor is already running")
            return
            
        self._stop_event.clear()
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("System monitor started")
        
    async def stop(self) -> None:
        """Stop the system monitoring."""
        if self._monitor_task is None:
            logger.warning("System monitor is not running")
            return
            
        self._stop_event.set()
        await self._monitor_task
        self._monitor_task = None
        logger.info("System monitor stopped")
        
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                metrics = await self._collect_metrics()
                self.metrics_history[metrics.timestamp] = metrics
                await self._check_thresholds(metrics)
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in monitor loop: {str(e)}", exc_info=True)
                await asyncio.sleep(1)  # Prevent tight loop on error
                
    async def _collect_metrics(self) -> SystemMetrics:
        """
        Collect system metrics.
        
        Returns:
            SystemMetrics object with current system state
        """
        timestamp = datetime.now()
        
        # Collect system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network_io = psutil.net_io_counters()
        
        # Determine system status
        status = self._determine_status(cpu_percent, memory.percent, disk.percent)
        
        # Get trading system status (to be implemented)
        trading_system_status = "OK"  # Placeholder
        mt5_connection_status = "Connected"  # Placeholder
        
        # Get performance metrics (to be implemented)
        performance_metrics = {}  # Placeholder
        
        return SystemMetrics(
            timestamp=timestamp,
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=disk.percent,
            network_io={
                'bytes_sent': network_io.bytes_sent,
                'bytes_recv': network_io.bytes_recv
            },
            status=status,
            trading_system_status=trading_system_status,
            mt5_connection_status=mt5_connection_status,
            performance_metrics=performance_metrics
        )
        
    def _determine_status(
        self,
        cpu_percent: float,
        memory_percent: float,
        disk_percent: float
    ) -> SystemStatus:
        """
        Determine system status based on thresholds.
        
        Args:
            cpu_percent: CPU usage percentage
            memory_percent: Memory usage percentage
            disk_percent: Disk usage percentage
            
        Returns:
            SystemStatus enum value
        """
        if (cpu_percent >= self.critical_thresholds['cpu_percent'] or
            memory_percent >= self.critical_thresholds['memory_percent'] or
            disk_percent >= self.critical_thresholds['disk_percent']):
            return SystemStatus.CRITICAL
            
        if (cpu_percent >= self.warning_thresholds['cpu_percent'] or
            memory_percent >= self.warning_thresholds['memory_percent'] or
            disk_percent >= self.warning_thresholds['disk_percent']):
            return SystemStatus.WARNING
            
        return SystemStatus.HEALTHY
        
    async def _check_thresholds(self, metrics: SystemMetrics) -> None:
        """
        Check metrics against thresholds and generate alerts if needed.
        
        Args:
            metrics: Current system metrics
        """
        if metrics.status == SystemStatus.CRITICAL:
            logger.critical(
                f"System in critical state: CPU={metrics.cpu_percent}%, "
                f"Memory={metrics.memory_percent}%, Disk={metrics.disk_percent}%"
            )
            # TODO: Implement alert system
        elif metrics.status == SystemStatus.WARNING:
            logger.warning(
                f"System in warning state: CPU={metrics.cpu_percent}%, "
                f"Memory={metrics.memory_percent}%, Disk={metrics.disk_percent}%"
            )
            # TODO: Implement alert system
            
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """
        Get the most recent system metrics.
        
        Returns:
            Most recent SystemMetrics object or None if no metrics available
        """
        if not self.metrics_history:
            return None
        return max(self.metrics_history.items())[1]
        
    def get_metrics_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[datetime, SystemMetrics]:
        """
        Get system metrics history within a time range.
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            Dictionary of timestamp to SystemMetrics
        """
        if not self.metrics_history:
            return {}
            
        if start_time is None:
            start_time = min(self.metrics_history.keys())
        if end_time is None:
            end_time = max(self.metrics_history.keys())
            
        return {
            ts: metrics
            for ts, metrics in self.metrics_history.items()
            if start_time <= ts <= end_time
        }
        
    def get_system_status(self) -> SystemStatus:
        """
        Get current system status.
        
        Returns:
            Current SystemStatus
        """
        current_metrics = self.get_current_metrics()
        if current_metrics is None:
            return SystemStatus.HEALTHY
        return current_metrics.status 