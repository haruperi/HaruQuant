"""Public execution API.

Thin facade over `services.execution`; implementation remains in services.
"""

from __future__ import annotations

from . import ServiceNamespace, load_service_module, resolve_service_attr, service_modules


_PRIORITY_MODULES = (
    "services.execution",
    "services.execution.approval",
    "services.execution.core",
    "services.execution.metadata_cache",
    "services.execution.pre_send",
    "services.execution.readiness",
    "services.execution.reconciliation",
    "services.execution.send_service",
    "services.execution.trade_action_governor",
    "services.execution.live",
    "services.execution.live.session",
)
_SERVICE_MODULES = _PRIORITY_MODULES + tuple(
    module
    for module in service_modules("services.execution")
    if module not in _PRIORITY_MODULES
)


class Execution(ServiceNamespace):
    _service_module = "services.execution"
    _service_modules = _SERVICE_MODULES

    @classmethod
    def approval(cls):
        return load_service_module("services.execution.approval")

    @classmethod
    def live(cls):
        return load_service_module("services.execution.live")

    @classmethod
    def monitoring(cls):
        return load_service_module("services.execution.monitoring")

    @classmethod
    def performance(cls):
        return load_service_module("services.execution.performance")

    @classmethod
    def reconciliation(cls):
        return load_service_module("services.execution.reconciliation")

    @classmethod
    def trade_governor(cls):
        return load_service_module("services.execution.trade_action_governor")


def __getattr__(name: str):
    return resolve_service_attr(name, _SERVICE_MODULES)


__all__ = ["Execution"]
