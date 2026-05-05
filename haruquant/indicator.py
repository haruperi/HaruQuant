"""Public indicator API.

Thin facade over `services.indicator`; implementation remains in services.
"""

from __future__ import annotations

from . import ServiceNamespace, resolve_service_attr, service_modules


_SERVICE_MODULES = service_modules("services.indicator")


class Indicator(ServiceNamespace):
    _service_module = "services.indicator"
    _service_modules = _SERVICE_MODULES


def __getattr__(name: str):
    return resolve_service_attr(name, _SERVICE_MODULES)


__all__ = ["Indicator"]
