"""Public research API.

Thin facade over `services.research`; implementation remains in services.
"""

from __future__ import annotations

from . import ServiceNamespace, load_service_module, resolve_service_attr, service_modules


_SERVICE_MODULES = service_modules("services.research")


class Research(ServiceNamespace):
    _service_module = "services.research"
    _service_modules = _SERVICE_MODULES

    @classmethod
    def modeling(cls):
        return load_service_module("services.research.modeling")


def __getattr__(name: str):
    return resolve_service_attr(name, _SERVICE_MODULES)


__all__ = ["Research"]
