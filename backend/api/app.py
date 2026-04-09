"""FastAPI application skeleton for the operator API."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .approvals import router as approvals_router
from .auth import OperatorAuthMiddleware, require_operator_role
from .dependencies import OperatorApiDependencies, build_operator_api_dependencies
from .health import (
    check_app_health,
    check_database_health,
    check_redis_health,
    check_schema_registry_health,
)


def get_operator_api_dependencies(request: Request) -> OperatorApiDependencies:
    """Expose the operator API dependency container to route handlers."""

    return request.app.state.operator_dependencies


def create_app(
    dependencies: OperatorApiDependencies | None = None,
) -> FastAPI:
    """Build the migration-era operator API application."""

    resolved_dependencies = dependencies or build_operator_api_dependencies()
    app = FastAPI(
        title="HaruQuant Operator API",
        description="Migration-era operator control plane skeleton.",
        version="0.1.0",
    )
    app.state.operator_dependencies = resolved_dependencies
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[resolved_dependencies.settings.ui_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(OperatorAuthMiddleware)

    router = APIRouter(prefix="/api/operator", tags=["operator"])

    @router.get("")
    def operator_api_metadata(request: Request) -> dict[str, object]:
        wired = get_operator_api_dependencies(request)
        principal = require_operator_role(request, "operator", "approver", "admin")
        return {
            "service": "haruquant-operator-api",
            "environment": wired.settings.environment,
            "schema_registry_contracts": len(wired.schema_registry.list_versions("WorkflowIntent")),
            "policy_bundle_count": len(wired.policy_resolver.bundles),
            "actor_id": principal.actor_id,
            "role": principal.role,
        }

    @router.get("/health")
    def operator_api_health(request: Request) -> dict[str, object]:
        wired = get_operator_api_dependencies(request)
        app_health = check_app_health(wired)
        db_health = check_database_health(wired)
        redis_health = check_redis_health(wired)
        schema_registry_health = check_schema_registry_health(wired)
        component_statuses = (
            app_health["status"],
            db_health["status"],
            redis_health["status"],
            schema_registry_health["status"],
        )
        overall_status = (
            "healthy"
            if all(status in {"healthy", "disabled"} for status in component_statuses)
            else "degraded"
        )
        return {
            "status": overall_status,
            "components": {
                "app": app_health,
                "db": db_health,
                "redis": redis_health,
                "schema_registry": schema_registry_health,
            },
        }

    @router.get("/health/db")
    def operator_api_database_health(request: Request) -> dict[str, object]:
        return check_database_health(get_operator_api_dependencies(request))

    @router.get("/health/redis")
    def operator_api_redis_health(request: Request) -> dict[str, object]:
        return check_redis_health(get_operator_api_dependencies(request))

    @router.get("/health/schema-registry")
    def operator_api_schema_registry_health(request: Request) -> dict[str, object]:
        return check_schema_registry_health(get_operator_api_dependencies(request))

    app.include_router(router)
    app.include_router(approvals_router)
    return app


app = create_app()
