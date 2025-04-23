# System Health Monitoring

## Overview

The system health monitoring module provides real-time monitoring of system resources and trading system status. It tracks CPU, memory, disk usage, network I/O, and trading system metrics to ensure optimal performance and early detection of potential issues.

## Features

- Real-time system resource monitoring (CPU, memory, disk)
- Network I/O monitoring
- Configurable warning and critical thresholds
- Historical metrics storage and retrieval
- Asynchronous monitoring with configurable update intervals
- Comprehensive error handling and logging
- Type-safe metrics collection and storage

## Components

### SystemStatus Enum

```python
class SystemStatus(Enum):
    HEALTHY = auto()    # System operating normally
    WARNING = auto()    # System approaching critical thresholds
    CRITICAL = auto()   # System in critical state
```

### SystemMetrics Dataclass

```python
@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    network_io: Dict[str, float]
    status: SystemStatus
    trading_system_status: str
    mt5_connection_status: str
    performance_metrics: Dict[str, float]
```

### SystemMonitor Class

The main monitoring class that handles all system health monitoring functionality.

#### Initialization

```python
monitor = SystemMonitor(
    update_interval=60.0,  # Time between metric updates in seconds
    warning_thresholds={   # Warning thresholds for system metrics
        'cpu_percent': 80.0,
        'memory_percent': 80.0,
        'disk_percent': 80.0
    },
    critical_thresholds={  # Critical thresholds for system metrics
        'cpu_percent': 90.0,
        'memory_percent': 90.0,
        'disk_percent': 90.0
    }
)
```

#### Methods

1. **Start Monitoring**
   ```python
   await monitor.start()
   ```
   Starts the system monitoring process.

2. **Stop Monitoring**
   ```python
   await monitor.stop()
   ```
   Stops the system monitoring process.

3. **Get Current Metrics**
   ```python
   current_metrics = monitor.get_current_metrics()
   ```
   Returns the most recent system metrics.

4. **Get Metrics History**
   ```python
   history = monitor.get_metrics_history(
       start_time=datetime.now() - timedelta(hours=1),
       end_time=datetime.now()
   )
   ```
   Returns system metrics history within a specified time range.

5. **Get System Status**
   ```python
   status = monitor.get_system_status()
   ```
   Returns the current system status (HEALTHY, WARNING, or CRITICAL).

## Usage Example

```python
from app.core.system_monitor import SystemMonitor
import asyncio

async def main():
    # Initialize monitor
    monitor = SystemMonitor(update_interval=60.0)
    
    try:
        # Start monitoring
        await monitor.start()
        
        # Monitor for some time
        await asyncio.sleep(300)  # 5 minutes
        
        # Get current status
        status = monitor.get_system_status()
        print(f"Current system status: {status}")
        
        # Get metrics history
        history = monitor.get_metrics_history()
        print(f"Collected {len(history)} metrics")
        
    finally:
        # Stop monitoring
        await monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### Default Thresholds

- **Warning Thresholds**:
  - CPU Usage: 80%
  - Memory Usage: 80%
  - Disk Usage: 80%

- **Critical Thresholds**:
  - CPU Usage: 90%
  - Memory Usage: 90%
  - Disk Usage: 90%

### Customizing Thresholds

```python
monitor = SystemMonitor(
    warning_thresholds={
        'cpu_percent': 75.0,
        'memory_percent': 75.0,
        'disk_percent': 75.0
    },
    critical_thresholds={
        'cpu_percent': 85.0,
        'memory_percent': 85.0,
        'disk_percent': 85.0
    }
)
```

## Error Handling

The system monitor includes comprehensive error handling:

1. **Monitor Loop Errors**: Errors in the monitoring loop are caught and logged, preventing the monitor from crashing.
2. **Resource Collection Errors**: Errors during metric collection are handled gracefully.
3. **Status Determination**: Invalid or missing metrics result in a HEALTHY status by default.

## Logging

The system monitor uses the project's logging system with appropriate log levels:

- **INFO**: Monitor start/stop events
- **WARNING**: System approaching critical thresholds
- **ERROR**: Monitor loop errors
- **CRITICAL**: System in critical state

## Testing

The module includes comprehensive unit tests covering:

1. Monitor start/stop functionality
2. Metric collection
3. Status determination
4. Threshold checking
5. Metrics history management
6. Error handling

To run the tests:
```bash
pytest tests/unit/core/test_system_monitor.py
```

## Future Enhancements

1. **Trading System Health Checks**
   - Monitor trading system components
   - Track order execution performance
   - Monitor strategy health

2. **MT5 Connection Monitoring**
   - Track connection status
   - Monitor API response times
   - Detect connection issues

3. **Alert System**
   - Email notifications
   - SMS alerts
   - Integration with monitoring dashboards

4. **Performance Metrics**
   - Trading performance tracking
   - System latency monitoring
   - Resource usage trends

5. **Monitoring Dashboard**
   - Real-time metrics visualization
   - Historical data analysis
   - Alert management interface 