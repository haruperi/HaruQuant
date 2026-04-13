"""OpenTelemetry export for distributed tracing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class OTelExportConfig:
    """Configuration for OpenTelemetry exporter."""
    service_name: str = "haruquant"
    exporter_endpoint: str = "http://localhost:14268/api/traces"  # Jaeger default
    sampling_rate: float = 1.0  # 1.0 = sample all traces


class OpenTelemetryExporter:
    """Exports traces to OpenTelemetry-compatible backends (Jaeger, Zipkin).

    Usage:
        exporter = OpenTelemetryExporter()
        exporter.export_trace(trace_data)

    Note: Requires opentelemetry-api, opentelemetry-sdk,
    and an exporter package (jaeger, zipkin, or otlp).
    """

    def __init__(self, config: OTelExportConfig | None = None) -> None:
        self._config = config or OTelExportConfig()
        self._initialized = False
        self._traces_exported = 0

    def export_trace(self, trace_data: Any) -> bool:
        """Export a trace to the configured backend.

        Returns True if export succeeded, False if not initialized.
        """
        if not self._initialized:
            self._try_initialize()
        if not self._initialized:
            return False
        # Placeholder — production would use actual OTel SDK
        self._traces_exported += 1
        return True

    def _try_initialize(self) -> None:
        """Try to initialize OpenTelemetry SDK."""
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({"service.name": self._config.service_name})
            provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(provider)
            self._initialized = True
        except ImportError:
            # OpenTelemetry packages not installed — silent fail
            self._initialized = False

    @property
    def traces_exported(self) -> int:
        return self._traces_exported
