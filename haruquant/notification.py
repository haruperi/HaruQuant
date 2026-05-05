"""Public notification API.

Thin facade over `services.notification`; implementation remains in services.
"""

from __future__ import annotations

from . import ServiceNamespace, load_service_module, resolve_service_attr, service_modules


_SERVICE_MODULES = service_modules("services.notification")


class Notification(ServiceNamespace):
    _service_module = "services.notification"
    _service_modules = _SERVICE_MODULES


def __getattr__(name: str):
    return resolve_service_attr(name, _SERVICE_MODULES)


__all__ = ["Notification"]
