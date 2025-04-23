"""
Async Framework for Concurrent Operations

This module provides a framework for managing concurrent operations in the trading system
using asyncio. It includes base classes for tasks, task managers, and utilities for
handling concurrent operations safely and efficiently.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto

from utils import get_logger

logger = get_logger(__name__)

class TaskStatus(Enum):
    """Status of a task in the system."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()

@dataclass
class TaskResult:
    """Result of a task execution."""
    status: TaskStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    error: Optional[Exception] = None
    data: Optional[Any] = None

class AsyncTask:
    """Base class for async tasks in the system."""
    
    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.result: Optional[TaskResult] = None
        self._task: Optional[asyncio.Task] = None
        
    async def execute(self) -> Any:
        """Execute the task's main logic. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")
    
    async def run(self) -> TaskResult:
        """Run the task and return its result."""
        self.status = TaskStatus.RUNNING
        start_time = datetime.utcnow()
        try:
            data = await self.execute()
            self.status = TaskStatus.COMPLETED
            self.result = TaskResult(
                status=TaskStatus.COMPLETED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                data=data
            )
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.result = TaskResult(
                status=TaskStatus.FAILED,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=e
            )
            logger.error(f"Task {self.name} failed: {str(e)}", exc_info=True)
        return self.result
    
    def cancel(self):
        """Cancel the task if it's running."""
        if self._task and not self._task.done():
            self._task.cancel()
            self.status = TaskStatus.CANCELLED

class TaskManager:
    """Manages concurrent execution of async tasks."""
    
    def __init__(self, max_concurrent_tasks: int = 10):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.tasks: Dict[str, AsyncTask] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
    async def add_task(self, task: AsyncTask) -> str:
        """Add a task to the manager and start its execution."""
        if task.name in self.tasks:
            raise ValueError(f"Task with name {task.name} already exists")
            
        self.tasks[task.name] = task
        task._task = asyncio.create_task(self._run_task(task))
        self._running_tasks[task.name] = task._task
        return task.name
    
    async def _run_task(self, task: AsyncTask) -> TaskResult:
        """Run a task with semaphore control."""
        async with self._semaphore:
            return await task.run()
    
    async def wait_for_task(self, task_name: str, timeout: Optional[float] = None) -> TaskResult:
        """Wait for a specific task to complete."""
        if task_name not in self.tasks:
            raise ValueError(f"Task {task_name} not found")
            
        task = self.tasks[task_name]
        if not task._task:
            raise ValueError(f"Task {task_name} is not running")
            
        try:
            await asyncio.wait_for(task._task, timeout)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task {task_name} timed out")
            
        return task.result
    
    async def wait_for_all(self, timeout: Optional[float] = None) -> Dict[str, TaskResult]:
        """Wait for all tasks to complete."""
        if not self._running_tasks:
            return {}
            
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._running_tasks.values()),
                timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError("Some tasks timed out")
            
        return {name: task.result for name, task in self.tasks.items()}
    
    def cancel_task(self, task_name: str):
        """Cancel a specific task."""
        if task_name in self.tasks:
            self.tasks[task_name].cancel()
    
    def cancel_all(self):
        """Cancel all running tasks."""
        for task in self.tasks.values():
            task.cancel()
    
    def get_task_status(self, task_name: str) -> TaskStatus:
        """Get the status of a specific task."""
        if task_name not in self.tasks:
            raise ValueError(f"Task {task_name} not found")
        return self.tasks[task_name].status
    
    def get_all_task_statuses(self) -> Dict[str, TaskStatus]:
        """Get the status of all tasks."""
        return {name: task.status for name, task in self.tasks.items()}

class PeriodicTask(AsyncTask):
    """Task that runs periodically."""
    
    def __init__(self, name: str, interval: float, func: Callable[[], Coroutine], priority: int = 0):
        super().__init__(name, priority)
        self.interval = interval
        self.func = func
        self._stop_event = asyncio.Event()
        
    async def execute(self) -> Any:
        """Execute the periodic task."""
        while not self._stop_event.is_set():
            try:
                await self.func()
            except Exception as e:
                logger.error(f"Error in periodic task {self.name}: {str(e)}", exc_info=True)
            await asyncio.sleep(self.interval)
    
    def stop(self):
        """Stop the periodic task."""
        self._stop_event.set()
        self.cancel()

class TaskGroup:
    """Group of related tasks that can be managed together."""
    
    def __init__(self, name: str):
        self.name = name
        self.tasks: List[AsyncTask] = []
        self._task_manager = TaskManager()
        
    async def add_task(self, task: AsyncTask):
        """Add a task to the group."""
        self.tasks.append(task)
        await self._task_manager.add_task(task)
    
    async def wait_for_all(self, timeout: Optional[float] = None) -> Dict[str, TaskResult]:
        """Wait for all tasks in the group to complete."""
        return await self._task_manager.wait_for_all(timeout)
    
    def cancel_all(self):
        """Cancel all tasks in the group."""
        self._task_manager.cancel_all()
    
    def get_task_statuses(self) -> Dict[str, TaskStatus]:
        """Get the status of all tasks in the group."""
        return self._task_manager.get_all_task_statuses() 