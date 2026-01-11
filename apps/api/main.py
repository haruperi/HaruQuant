"""FastAPI application main entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.logger import logger

from .logging_config import setup_logging
from .routes import (
    auth,
    broker,
    data,
    docs,
    live,
    market_hours,
    optimization,
    settings,
    strategies,
    system,
    trades,
)
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
app.include_router(system.router, prefix="/api/system", tags=["system"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(broker.router, prefix="/api/broker", tags=["broker"])
app.include_router(
    market_hours.router, prefix="/api/market-hours", tags=["market-hours"]
)
app.include_router(trades.router, prefix="/api/trades", tags=["trades"])
app.include_router(live.router, prefix="/api/live", tags=["live-trading"])
app.include_router(data.router, prefix="/api/data", tags=["data-management"])
app.include_router(
    optimization.router, prefix="/api/optimization", tags=["optimization"]
)
app.include_router(docs.router, prefix="/api/docs", tags=["docs"])
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


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down HaruQuant API server")


@app.get("/api/health")
async def health_check():
    """Return health check status."""
    return {"status": "healthy", "service": "haruquant-api"}
