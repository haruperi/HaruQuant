"""Public analytics API.

Thin facade over `services.analytics`; implementation remains in services.
"""

from __future__ import annotations

from . import ServiceNamespace, load_service_module, resolve_service_attr, service_modules


_SERVICE_MODULES = service_modules("services.analytics")


class Analytics(ServiceNamespace):
    _service_module = "services.analytics"
    _service_modules = _SERVICE_MODULES

    @classmethod
    def overview(cls):
        return load_service_module("services.analytics.overview")

    @classmethod
    def metrics(cls):
        return load_service_module("services.analytics.metrics")

    @classmethod
    def returns(cls):
        return load_service_module("services.analytics.returns")

    @classmethod
    def drawdowns(cls):
        return load_service_module("services.analytics.drawdowns")

    @classmethod
    def ratios(cls):
        return load_service_module("services.analytics.ratios")

    @classmethod
    def risks(cls):
        return load_service_module("services.analytics.risks")


def __getattr__(name: str):
    return resolve_service_attr(name, _SERVICE_MODULES)


__all__ = ["Analytics"]
