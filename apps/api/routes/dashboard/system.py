"""System status and resources routes."""

import sqlite3

from fastapi import APIRouter

from apps.api.models import ResourceUsageResponse, SystemStatusResponse
from apps.logger import logger
from apps.sqlite.database_operations import DatabaseManager

# Try to import psutil, handle if missing
try:
    import psutil
except ImportError:
    psutil = None
    logger.warning("psutil not found. Resource usage will be unavailable.")

router = APIRouter()


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get backend and database status."""
    db = DatabaseManager()
    db_status = "Disconnected"
    message = ""

    try:
        # Simple query to check connection
        conn = sqlite3.connect(db.db_path)
        conn.execute("SELECT 1")
        conn.close()
        db_status = "Connected"
        message = "All systems operational"
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        db_status = "Error"
        message = str(e)

    return SystemStatusResponse(
        backend="Operational", database=db_status, message=message
    )


@router.get("/system/resources", response_model=ResourceUsageResponse)
async def get_resource_usage():
    """Get system resource usage (CPU, Memory)."""
    if not psutil:
        return ResourceUsageResponse(
            cpu_percent=0.0,
            memory_percent=0.0,
            memory_used_gb=0.0,
            memory_total_gb=8.0,  # fallback default
        )

    try:
        cpu_percent = psutil.cpu_percent(interval=None)  # Non-blocking
        mem = psutil.virtual_memory()

        return ResourceUsageResponse(
            cpu_percent=cpu_percent,
            memory_percent=mem.percent,
            memory_used_gb=round(mem.used / (1024**3), 2),
            memory_total_gb=round(mem.total / (1024**3), 2),
        )
    except Exception as e:
        logger.error(f"Error fetching resources: {e}")
        return ResourceUsageResponse(
            cpu_percent=0.0, memory_percent=0.0, memory_used_gb=0.0, memory_total_gb=0.0
        )
