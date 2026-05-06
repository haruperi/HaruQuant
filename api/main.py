"""FastAPI application main entry point."""

from contextlib import asynccontextmanager
import importlib

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from haruquant.utils import logger
from api.middleware.security import SecretRedactionMiddleware
from api.router import intent_classifier

def _optional_import(module_path: str, label: str):
    try:
        return importlib.import_module(module_path, package=__package__)
    except Exception as exc:
        logger.warning(f"{label} disabled during API startup: {exc}")
        return None


optimization = _optional_import('.routes.optimization', 'Optimization route')
live = _optional_import('.routes.live', 'Live route')
edge = _optional_import('.routes.edge', 'Edge route')
data = _optional_import('.routes.data', 'Data route')
ai_chat = _optional_import('.routes.ai_chat', 'AI chat route')
auth = _optional_import('.routes.auth', 'Auth route')
backtest = _optional_import('.routes.backtest', 'Backtest route')
docs = _optional_import('.routes.docs', 'Docs route')
risk = _optional_import('.routes.risk', 'Risk route')
settings = _optional_import('.routes.settings', 'Settings route')
simulator = _optional_import('.routes.simulator', 'Simulator route')
sqx = _optional_import('.routes.sqx', 'SQX route')
strategies = _optional_import('.routes.strategies', 'Strategies route')
operator_strategies = _optional_import('.routes.operator_strategies', 'Operator strategies route')
dashboard_broker = _optional_import('.routes.dashboard.broker', 'Dashboard broker route')
dashboard_currency_strength = _optional_import('.routes.dashboard.currency_strength', 'Dashboard currency-strength route')
dashboard_forex_calendar = _optional_import('.routes.dashboard.forex_calendar', 'Dashboard forex-calendar route')
dashboard_market_hours = _optional_import('.routes.dashboard.market_hours', 'Dashboard market-hours route')
dashboard_system = _optional_import('.routes.dashboard.system', 'Dashboard system route')


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting HaruQuant API server")

    from data.database.sqlite.database_operations import DatabaseManager
    from data.database import apply_pending_migrations, default_migrations_dir
    from api.scheduler import start_scheduler

    try:
        db = DatabaseManager()
        db.initialize_database()
        apply_pending_migrations(db.db_path, default_migrations_dir())
        if simulator is not None:
            simulator.cleanup_stale_simulation_leases()
        logger.info("Database initialized successfully on startup.")
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}")

    yield

    # Shutdown
    logger.info("Shutting down HaruQuant API server")
    from api.scheduler import shutdown_scheduler

    shutdown_scheduler()


# Create FastAPI app
app = FastAPI(
    title="HaruQuant API",
    description="Backend API for HaruQuant trading platform",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecretRedactionMiddleware)


# Intent classification middleware — attaches routing metadata to every request
class IntentClassificationMiddleware(BaseHTTPMiddleware):
    """Classify request intent and attach routing metadata."""

    async def dispatch(self, request: Request, call_next):
        metadata = intent_classifier.classify_and_metadata(
            request.url.path,
            session_id=request.headers.get("X-Session-ID"),
        )
        request.state.intent = metadata.intent
        request.state.priority = metadata.priority
        request.state.session_id = metadata.session_id
        request.state.user_id = metadata.user_id
        return await call_next(request)


app.add_middleware(IntentClassificationMiddleware)


def _include_optional_router(app: FastAPI, module, prefix: str, tags: list[str]) -> None:
    if module is not None:
        app.include_router(module.router, prefix=prefix, tags=tags)


# Include routers
_include_optional_router(app, auth, prefix="/api/auth", tags=["authentication"])
_include_optional_router(app, settings, prefix="/api/settings", tags=["settings"])
_include_optional_router(app, ai_chat, prefix="/api/ai-chat", tags=["ai-chat"])

_include_optional_router(app, strategies, prefix="/api/strategies", tags=["strategies"])
_include_optional_router(app, operator_strategies, prefix="/api/operator", tags=["operator-strategies"])
_include_optional_router(app, sqx, prefix="/api/sqx", tags=["sqx"])
_include_optional_router(app, backtest, prefix="/api/backtest", tags=["backtest"])
_include_optional_router(app, simulator, prefix="/api/simulator", tags=["simulator"])
_include_optional_router(app, risk, prefix="/api/risk", tags=["risk"])
_include_optional_router(app, live, prefix="/api/live", tags=["live"])
_include_optional_router(app, optimization, prefix="/api/optimization", tags=["optimization"])

# Dashboard Routes
_include_optional_router(app, dashboard_broker, prefix="/api/dashboard", tags=["dashboard"])
_include_optional_router(app, dashboard_system, prefix="/api/dashboard", tags=["dashboard"])
_include_optional_router(app, dashboard_market_hours, prefix="/api/dashboard", tags=["dashboard"])
_include_optional_router(app, dashboard_currency_strength, prefix="/api/dashboard", tags=["dashboard"])
_include_optional_router(app, dashboard_forex_calendar, prefix="/api/dashboard", tags=["dashboard"])

_include_optional_router(app, docs, prefix="/api/docs", tags=["docs"])
_include_optional_router(app, edge, prefix="/api/edge-lab", tags=["edge-lab"])
_include_optional_router(app, data, prefix="/api/data", tags=["data"])


@app.get("/api/health")
async def health_check():
    """Return health check status."""
    return {"status": "healthy", "service": "haruquant-api"}
