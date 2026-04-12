"""FastAPI application main entry point."""

from contextlib import asynccontextmanager
import importlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.common.logger import logger
from backend.api.legacy.middleware.security import SecretRedactionMiddleware

from .routes import (
    auth,
    backtest,
    docs,
    risk,
    settings,
    simulator,
    sqx,
    strategies,
)

def _optional_import(module_path: str, label: str):
    try:
        return importlib.import_module(module_path, package=__package__)
    except Exception as exc:
        logger.warning(f"{label} disabled during API startup: {exc}")
        return None


optimization = _optional_import('.routes.optimization', 'Optimization route')
live = _optional_import('.routes.live', 'Live route')
edge = _optional_import('.routes.edge', 'Edge route')
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

    from apps.sqlite.database_operations import DatabaseManager
    from backend.api.legacy.scheduler import start_scheduler

    try:
        db = DatabaseManager()
        db.initialize_database()
        simulator.cleanup_stale_simulation_leases()
        logger.info("Database initialized successfully on startup.")
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}")

    yield

    # Shutdown
    logger.info("Shutting down HaruQuant API server")
    from backend.api.legacy.scheduler import shutdown_scheduler

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

def _include_optional_router(app: FastAPI, module, prefix: str, tags: list[str]) -> None:
    if module is not None:
        app.include_router(module.router, prefix=prefix, tags=tags)


# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(sqx.router, prefix="/api/sqx", tags=["sqx"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(simulator.router, prefix="/api/simulator", tags=["simulator"])
app.include_router(risk.router, prefix="/api/risk", tags=["risk"])
_include_optional_router(app, live, prefix="/api/live", tags=["live"])
_include_optional_router(app, optimization, prefix="/api/optimization", tags=["optimization"])

# Dashboard Routes
_include_optional_router(app, dashboard_broker, prefix="/api/dashboard", tags=["dashboard"])
_include_optional_router(app, dashboard_system, prefix="/api/dashboard", tags=["dashboard"])
_include_optional_router(app, dashboard_market_hours, prefix="/api/dashboard", tags=["dashboard"])
_include_optional_router(app, dashboard_currency_strength, prefix="/api/dashboard", tags=["dashboard"])
_include_optional_router(app, dashboard_forex_calendar, prefix="/api/dashboard", tags=["dashboard"])

app.include_router(docs.router, prefix="/api/docs", tags=["docs"])
_include_optional_router(app, edge, prefix="/api/edge-lab", tags=["edge-lab"])


@app.get("/api/health")
async def health_check():
    """Return health check status."""
    return {"status": "healthy", "service": "haruquant-api"}


