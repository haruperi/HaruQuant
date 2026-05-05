"""Public simulation API.

Thin facade over `services.simulation`; implementation remains in services.
"""

from __future__ import annotations

from . import ServiceNamespace, load_service_module, resolve_service_attr, service_modules


_SERVICE_MODULES = service_modules("services.simulation")


class Simulation(ServiceNamespace):
    _service_module = "services.simulation"
    _service_modules = _SERVICE_MODULES

    @classmethod
    def engine(cls):
        return load_service_module("services.simulation.engine")

    @classmethod
    def runner(cls):
        return load_service_module("services.simulation.runner")

    @classmethod
    def results(cls):
        return load_service_module("services.simulation.results")


def __getattr__(name: str):
    return resolve_service_attr(name, _SERVICE_MODULES)


__all__ = ["Simulation"]
