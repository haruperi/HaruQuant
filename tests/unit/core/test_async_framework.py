"""
Tests for the async framework implementation.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from app.core.async_framework import (
    AsyncTask,
    TaskManager,
    TaskStatus,
    TaskResult,
    PeriodicTask,
    TaskGroup
)

class TestAsyncTask(AsyncTask):
    """Test implementation of AsyncTask."""
    
    def __init__(self, name: str, result: Any = None, error: Exception = None):
        super().__init__(name)
        self._result = result
        self._error = error
        
    async def execute(self) -> Any:
        if self._error:
            raise self._error
        return self._result

@pytest.mark.asyncio
async def test_async_task_success():
    """Test successful task execution."""
    task = TestAsyncTask("test_task", result="success")
    result = await task.run()
    
    assert result.status == TaskStatus.COMPLETED
    assert result.data == "success"
    assert result.error is None
    assert isinstance(result.start_time, datetime)
    assert isinstance(result.end_time, datetime)

@pytest.mark.asyncio
async def test_async_task_failure():
    """Test task execution with error."""
    error = ValueError("Test error")
    task = TestAsyncTask("test_task", error=error)
    result = await task.run()
    
    assert result.status == TaskStatus.FAILED
    assert result.data is None
    assert result.error == error
    assert isinstance(result.start_time, datetime)
    assert isinstance(result.end_time, datetime)

@pytest.mark.asyncio
async def test_task_manager():
    """Test TaskManager functionality."""
    manager = TaskManager(max_concurrent_tasks=2)
    
    # Add tasks
    task1 = TestAsyncTask("task1", result="result1")
    task2 = TestAsyncTask("task2", result="result2")
    task3 = TestAsyncTask("task3", result="result3")
    
    await manager.add_task(task1)
    await manager.add_task(task2)
    await manager.add_task(task3)
    
    # Wait for all tasks
    results = await manager.wait_for_all()
    
    assert len(results) == 3
    assert results["task1"].data == "result1"
    assert results["task2"].data == "result2"
    assert results["task3"].data == "result3"
    
    # Check task statuses
    statuses = manager.get_all_task_statuses()
    assert all(status == TaskStatus.COMPLETED for status in statuses.values())

@pytest.mark.asyncio
async def test_task_manager_timeout():
    """Test TaskManager timeout handling."""
    manager = TaskManager()
    
    async def long_running_task():
        await asyncio.sleep(2)
        return "result"
    
    task = TestAsyncTask("long_task")
    task.execute = long_running_task
    
    await manager.add_task(task)
    
    with pytest.raises(TimeoutError):
        await manager.wait_for_all(timeout=0.1)

@pytest.mark.asyncio
async def test_periodic_task():
    """Test PeriodicTask functionality."""
    counter = 0
    
    async def increment_counter():
        nonlocal counter
        counter += 1
    
    task = PeriodicTask("periodic", interval=0.1, func=increment_counter)
    task._task = asyncio.create_task(task.run())
    
    # Let it run for a while
    await asyncio.sleep(0.5)
    
    # Stop the task
    task.stop()
    
    # Wait for it to finish
    await task._task
    
    assert counter > 0
    assert task.status == TaskStatus.CANCELLED

@pytest.mark.asyncio
async def test_task_group():
    """Test TaskGroup functionality."""
    group = TaskGroup("test_group")
    
    task1 = TestAsyncTask("task1", result="result1")
    task2 = TestAsyncTask("task2", result="result2")
    
    await group.add_task(task1)
    await group.add_task(task2)
    
    results = await group.wait_for_all()
    
    assert len(results) == 2
    assert results["task1"].data == "result1"
    assert results["task2"].data == "result2"
    
    statuses = group.get_task_statuses()
    assert all(status == TaskStatus.COMPLETED for status in statuses.values())

@pytest.mark.asyncio
async def test_task_cancellation():
    """Test task cancellation."""
    manager = TaskManager()
    
    async def never_ending_task():
        while True:
            await asyncio.sleep(0.1)
    
    task = TestAsyncTask("infinite_task")
    task.execute = never_ending_task
    
    await manager.add_task(task)
    
    # Cancel the task
    manager.cancel_task("infinite_task")
    
    # Wait for cancellation to complete
    await asyncio.sleep(0.1)
    
    assert task.status == TaskStatus.CANCELLED

@pytest.mark.asyncio
async def test_task_priority():
    """Test task priority handling."""
    manager = TaskManager(max_concurrent_tasks=1)
    
    execution_order = []
    
    async def record_execution(name: str):
        execution_order.append(name)
        await asyncio.sleep(0.1)
    
    # Create tasks with different priorities
    task1 = TestAsyncTask("task1", priority=1)
    task1.execute = lambda: record_execution("task1")
    
    task2 = TestAsyncTask("task2", priority=2)
    task2.execute = lambda: record_execution("task2")
    
    task3 = TestAsyncTask("task3", priority=3)
    task3.execute = lambda: record_execution("task3")
    
    # Add tasks in reverse priority order
    await manager.add_task(task3)
    await manager.add_task(task2)
    await manager.add_task(task1)
    
    # Wait for all tasks to complete
    await manager.wait_for_all()
    
    # Tasks should execute in priority order (higher priority first)
    assert execution_order == ["task3", "task2", "task1"] 