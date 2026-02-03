"""FastAPI application main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.logger import logger

from .logging_config import setup_logging
from .routes import (
    auth,
    backtest,
    docs,
    edge,
    live,
    optimization,
    settings,
    simulator,
    sqx,
    strategies,
)
from .routes.dashboard import broker as dashboard_broker
from .routes.dashboard import currency_strength as dashboard_currency_strength
from .routes.dashboard import market_hours as dashboard_market_hours
from .routes.dashboard import system as dashboard_system
from .routes.data import datasets as data_datasets
from .routes.data import ingestion as data_ingestion
from .routes.reports import trades  # Moved here
from .routes.reports import (
    consecutive_winners_losers,
    equity_curve,
    equity_performance,
    losing_trades,
    outliers,
    performance_ratio_chart,
    performance_ratios,
    periodical_analysis,
    risk_distribution,
    runup_drawdown,
    series_analysis,
    series_stats,
    strategy_performance,
    time_analysis,
    total_analysis,
    total_trades,
    trade_list,
    winning_trades,
)

# Create FastAPI app
app = FastAPI(
    title="HaruQuant API",
    description="Backend API for HaruQuant trading platform",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(sqx.router, prefix="/api/sqx", tags=["sqx"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(live.router, prefix="/api/live", tags=["live"])
app.include_router(
    optimization.router, prefix="/api/optimization", tags=["optimization"]
)

# Dashboard Routes
app.include_router(dashboard_broker.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(dashboard_system.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(
    dashboard_market_hours.router, prefix="/api/dashboard", tags=["dashboard"]
)
app.include_router(
    dashboard_currency_strength.router, prefix="/api/dashboard", tags=["dashboard"]
)

app.include_router(trades.router, prefix="/api/reports/trades", tags=["trades"])
app.include_router(data_ingestion.router, prefix="/api/data", tags=["data-management"])
app.include_router(data_datasets.router, prefix="/api/data", tags=["data-management"])
app.include_router(docs.router, prefix="/api/docs", tags=["docs"])
app.include_router(edge.router, prefix="/api/edge-lab", tags=["edge-lab"])
app.include_router(strategy_performance.router, prefix="/api/reports", tags=["reports"])
app.include_router(performance_ratios.router, prefix="/api/reports", tags=["reports"])
app.include_router(time_analysis.router, prefix="/api/reports", tags=["reports"])
app.include_router(equity_curve.router, prefix="/api/reports", tags=["reports"])
app.include_router(trade_list.router, prefix="/api/reports", tags=["reports"])
app.include_router(total_trades.router, prefix="/api/reports", tags=["reports"])
app.include_router(winning_trades.router, prefix="/api/reports", tags=["reports"])
app.include_router(losing_trades.router, prefix="/api/reports", tags=["reports"])
app.include_router(total_analysis.router, prefix="/api/reports", tags=["reports"])
app.include_router(outliers.router, prefix="/api/reports", tags=["reports"])
app.include_router(runup_drawdown.router, prefix="/api/reports", tags=["reports"])
app.include_router(series_analysis.router, prefix="/api/reports", tags=["reports"])
app.include_router(series_stats.router, prefix="/api/reports", tags=["reports"])
app.include_router(periodical_analysis.router, prefix="/api/reports", tags=["reports"])
app.include_router(equity_performance.router, prefix="/api/reports", tags=["reports"])
app.include_router(
    consecutive_winners_losers.router, prefix="/api/reports", tags=["reports"]
)
app.include_router(
    performance_ratio_chart.router, prefix="/api/reports", tags=["reports"]
)
app.include_router(risk_distribution.router, prefix="/api/reports", tags=["reports"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    setup_logging()
    logger.info("Starting HaruQuant API server")

    # Initialize database
    from apps.scheduler import start_scheduler
    from apps.sqlite.database_operations import DatabaseManager

    try:
        db = DatabaseManager()
        db.initialize_database()
        logger.info("Database initialized successfully on startup.")
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to initialize database on startup: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down HaruQuant API server")
    from apps.scheduler import shutdown_scheduler

    shutdown_scheduler()


@app.get("/api/health")
async def health_check():
    """Return health check status."""
    return {"status": "healthy", "service": "haruquant-api"}


app.include_router(simulator.router, prefix="/api/simulator", tags=["simulator"])
