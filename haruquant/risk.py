"""Public risk API.

Thin facade over `services.risk`; implementation remains in services.
"""

from __future__ import annotations

from . import ServiceNamespace, load_service_module, resolve_service_attr, service_modules


_PRIORITY_MODULES = (
    "services.risk",
    "services.risk.metrics.base",
    "services.risk.scoring.base",
    "services.risk.policy",
    "services.risk.policy.compliance_rollout",
    "services.risk.portfolio",
    "services.risk.safety",
)
_SERVICE_MODULES = _PRIORITY_MODULES + tuple(
    module
    for module in service_modules("services.risk")
    if module not in _PRIORITY_MODULES and not module.startswith("services.risk.live")
)


class Risk(ServiceNamespace):
    _service_module = "services.risk"
    _service_modules = _SERVICE_MODULES

    @classmethod
    def policy(cls):
        return load_service_module("services.risk.policy")

    @classmethod
    def portfolio(cls):
        return load_service_module("services.risk.portfolio")

    @classmethod
    def safety(cls):
        return load_service_module("services.risk.safety")

    @classmethod
    def live(cls):
        return load_service_module("services.risk.live")


def __getattr__(name: str):
    return resolve_service_attr(name, _SERVICE_MODULES)


__all__ = ["Risk"]
