"""HaruQuant public API.

This package is the public facade over `services`. Implementation belongs in
`services`; callers should import `haruquant` and use the exported namespaces.
"""

from __future__ import annotations

from importlib import import_module
from pkgutil import walk_packages
from types import ModuleType
from typing import Any


def load_service_symbol(*, service_module: str, name: str) -> Any:
    module = import_module(service_module)
    value = getattr(module, name)
    return value


def load_service_module(service_module: str) -> ModuleType:
    return import_module(service_module)


def service_modules(service_package: str) -> tuple[str, ...]:
    package = import_module(service_package)
    modules = [service_package]
    package_paths = getattr(package, "__path__", None)
    if package_paths is None:
        return tuple(modules)
    modules.extend(
        module_info.name
        for module_info in walk_packages(package_paths, prefix=f"{service_package}.")
    )
    return tuple(modules)


def resolve_service_attr(name: str, modules: tuple[str, ...]) -> Any:
    last_error: AttributeError | None = None
    for module_name in modules:
        module = import_module(module_name)
        if hasattr(module, name):
            value = getattr(module, name)
            if not (isinstance(value, ModuleType) and value.__name__ == f"{module_name}.{name}"):
                return value
        try:
            submodule = import_module(f"{module_name}.{name}")
            return getattr(submodule, name) if hasattr(submodule, name) else submodule
        except ModuleNotFoundError as exc:
            if exc.name != f"{module_name}.{name}":
                raise
            last_error = AttributeError(name)
    raise last_error or AttributeError(name)


class ServiceNamespace:
    """VectorBT-style namespace that forwards attributes to a service module."""

    _service_module: str
    _service_modules: tuple[str, ...] = ()

    @classmethod
    def _module(cls) -> ModuleType:
        return load_service_module(cls._service_module)

    @classmethod
    def get(cls, name: str) -> Any:
        modules = cls._service_modules or (cls._service_module,)
        return resolve_service_attr(name, modules)


_EXPORTS: dict[str, tuple[str, str]] = {
    # Data
    "Data": (".data", "Data"),
    "DataCache": (".data", "DataCache"),
    "MT5Data": (".data", "MT5Data"),
    "DukascopyData": (".data", "DukascopyData"),
    "YFData": (".data", "YFData"),
    "BinanceData": (".data", "BinanceData"),
    "CCXTData": (".data", "CCXTData"),
    "CSVData": (".data", "CSVData"),
    "ParquetData": (".data", "ParquetData"),
    "GBMData": (".data", "GBMData"),
    "ScheduledDataUpdater": (".data", "ScheduledDataUpdater"),
    "Labeler": (".data", "Labeler"),
    "DataSaver": (".data", "DataSaver"),
    "CSVDataSaver": (".data", "CSVDataSaver"),
    "ParquetDataSaver": (".data", "ParquetDataSaver"),
    # Utilities
    "resample": (".utils", "resample"),
    "merge": (".utils", "merge"),
    "concat": (".utils", "concat"),
    "symbol_dict": (".utils", "symbol_dict"),
    "Param": (".utils", "Param"),
    "combine_params": (".utils", "combine_params"),
    "rolling_mean": (".utils", "rolling_mean"),
    "chunked": (".utils", "chunked"),
    # Indicator
    "ema": (".indicator", "ema"),
    "sma": (".indicator", "sma"),
    "rsi": (".indicator", "rsi"),
    "bbands": (".indicator", "bbands"),
    "atr": (".indicator", "atr"),
    "hurst": (".indicator", "hurst"),
    "fvg": (".indicator", "fvg"),
    "ob": (".indicator", "ob"),
    "bos_choch": (".indicator", "bos_choch"),
    "phl": (".indicator", "phl"),
    "ta": (".indicator", "ta"),
    "list_indicators": (".indicator", "list_indicators"),
    "indicator": (".indicator", "indicator"),
    "run_indicators": (".indicator", "run_indicators"),
    # Strategy and optimization
    "Catalog": (".strategy", "Catalog"),
    "Portfolio": (".strategy", "Portfolio"),
    "StrategyCatalogCreateRequest": (".strategy", "StrategyCatalogCreateRequest"),
    "StrategyCatalogUpdateRequest": (".strategy", "StrategyCatalogUpdateRequest"),
    "TrendFollowingStrategy": (".strategy", "TrendFollowingStrategy"),
    "BreakoutStrategy": (".strategy", "BreakoutStrategy"),
    "MeanReversionStrategy": (".strategy", "MeanReversionStrategy"),
    "CloseBreakoutStrategy": (".strategy", "CloseBreakoutStrategy"),
    "Optimizer": (".optimization", "Optimizer"),
    "Splitter": (".optimization", "Splitter"),
    "PortfolioOptimizer": (".optimization", "PortfolioOptimizer"),
    "PFO": (".optimization", "PortfolioOptimizer"),
    "grid_search": (".optimization", "Optimizer.grid_search"),
    "random_search": (".optimization", "Optimizer.random_search"),
    "bayesian": (".optimization", "Optimizer.bayesian"),
    "genetic": (".optimization", "Optimizer.genetic"),
    "walk_forward": (".optimization", "Optimizer.walk_forward"),
    "monte_carlo": (".optimization", "Optimizer.monte_carlo"),
    # Domain namespaces
    "Analytics": (".analytics", "Analytics"),
    "Execution": (".execution", "Execution"),
    "Notification": (".notification", "Notification"),
    "Research": (".research", "Research"),
    "Risk": (".risk", "Risk"),
    "Simulation": (".simulation", "Simulation"),
    "Utils": (".utils", "Utils"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(name) from exc
    module = import_module(module_name, __name__)
    value: Any = module
    for part in attr_name.split("."):
        value = getattr(value, part)
    globals()[name] = value
    return value


__all__ = sorted(_EXPORTS)
