
import sys
from unittest.mock import MagicMock

# Mock apscheduler
sys.modules["apscheduler"] = MagicMock()
sys.modules["apscheduler.schedulers"] = MagicMock()
sys.modules["apscheduler.schedulers.asyncio"] = MagicMock()
sys.modules["apscheduler.triggers"] = MagicMock()
sys.modules["apscheduler.triggers.cron"] = MagicMock()

# Mock MetaTrader5
sys.modules["MetaTrader5"] = MagicMock()

# Mock fastAPI and uvicorn if needed (apps/api uses them)
try:
    import fastapi
except ImportError:
    sys.modules["fastapi"] = MagicMock()
    sys.modules["fastapi.security"] = MagicMock()

try:
    import uvicorn
except ImportError:
    sys.modules["uvicorn"] = MagicMock()

# Ensure apps.sqlite is mocked if needed for scheduler test
# Actually, let's just let it be, if it exists it's fine. 
# But let's mock DatabaseManager just in case it fails import
try:
    from apps.sqlite.database_operations import DatabaseManager
except ImportError:
    # Use nested mocks to simulate structure
    mock_sqlite = MagicMock()
    sys.modules["apps.sqlite"] = mock_sqlite
    sys.modules["apps.sqlite.database_operations"] = MagicMock()
