"""FastAPI application skeleton for the operator API."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .dependencies import OperatorApiDependencies, build_operator_api_dependencies


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

    router = APIRouter(prefix="/api/operator", tags=["operator"])

    @router.get("")
    def operator_api_metadata(request: Request) -> dict[str, object]:
        wired = get_operator_api_dependencies(request)
        return {
            "service": "haruquant-operator-api",
            "environment": wired.settings.environment,
            "schema_registry_contracts": len(wired.schema_registry.list_versions("WorkflowIntent")),
            "policy_bundle_count": len(wired.policy_resolver.bundles),
        }

    app.include_router(router)
    return app


app = create_app()
