"""Public indicator API.

Thin facade over `services.indicator`; implementation remains in services.
"""

from __future__ import annotations

from dataclasses import dataclass
import fnmatch
import inspect
import sys
from typing import Any, Callable, Iterable

import pandas as pd

from . import ServiceNamespace, resolve_service_attr, service_modules


_SERVICE_MODULES = service_modules("services.indicator")

_PARAM_ALIASES = {
    "ema": "span",
    "sma": "window",
    "wma": "window",
    "rsi": "period",
    "bbands": "period",
    "atr": "period",
    "hurst": "period",
    "fvg": None,
    "ob": "swing_length",
    "bos_choch": "swing_length",
    "phl": "timeframe",
    "previous_high_low": "timeframe",
}

_ALIASES = {
    "phl": "previous_high_low",
}

_INDICATORS = {
    "ema": "native",
    "sma": "native",
    "wma": "native",
    "rsi": "native",
    "bbands": "native",
    "atr": "native",
    "hurst": "native",
    "fvg": "smc",
    "ob": "smc",
    "bos_choch": "smc",
    "phl": "smc",
}


def _as_frame(data: Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data
    frame = getattr(data, "df", None)
    if isinstance(frame, pd.DataFrame):
        return frame
    raise TypeError("Indicator input must be a pandas DataFrame or hqt.Data object.")


def _is_many(value: Any) -> bool:
    return isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict))


def _service_function(name: str) -> Callable[..., pd.DataFrame]:
    service_name = _ALIASES.get(name, name)
    value = resolve_service_attr(service_name, _SERVICE_MODULES)
    if not callable(value):
        raise TypeError(f"Indicator '{name}' resolved to a non-callable service object.")
    return value


@dataclass(frozen=True)
class IndicatorRunner:
    """VectorBT-style callable indicator facade."""

    name: str

    def __call__(self, data: Any, *args: Any, **kwargs: Any) -> pd.DataFrame:
        return self.run(data, *args, **kwargs)

    def run(self, data: Any, period: Any = None, **kwargs: Any) -> pd.DataFrame:
        frame = _as_frame(data)
        func = _service_function(self.name)
        service_name = _ALIASES.get(self.name, self.name)
        period_param = _PARAM_ALIASES.get(self.name, "period")

        engine = kwargs.pop("engine", None)
        kwargs.pop("n_workers", None)
        if engine not in (None, "serial", "threadpool"):
            raise ValueError(f"Unsupported indicator engine: {engine}")

        if period is None and period_param and period_param in kwargs:
            period = kwargs.pop(period_param)

        if period_param is None:
            if period is not None and service_name != "fvg":
                kwargs["period"] = period
            return func(frame, **kwargs)

        if period is None:
            return func(frame, **kwargs)

        periods = list(period) if _is_many(period) else [period]
        result = frame.copy()
        for item in periods:
            result = func(result, **{period_param: item}, **kwargs)
        return result


class TAAccessor:
    """Pandas TA Classic facade that appends generated columns to input data."""

    def __getattr__(self, name: str) -> Callable[..., pd.DataFrame]:
        def _run(data: Any, period: Any = None, **kwargs: Any) -> pd.DataFrame:
            return self.run(name, data, period=period, **kwargs)

        return _run

    def run(self, name: str, data: Any, period: Any = None, **kwargs: Any) -> pd.DataFrame:
        try:
            import pandas_ta_classic as ta_lib
        except ImportError as exc:
            raise ImportError(
                "pandas_ta_classic is required for hqt.ta indicators."
            ) from exc

        func = getattr(ta_lib, name)
        source = _as_frame(data)
        result = source.copy()
        periods = [period] if period is None or not _is_many(period) else list(period)

        for item in periods:
            call_kwargs = dict(kwargs)
            if item is not None:
                call_kwargs.setdefault("length", item)
            inputs = {
                "close": result["close"] if "close" in result else None,
                "high": result["high"] if "high" in result else None,
                "low": result["low"] if "low" in result else None,
                "open": result["open"] if "open" in result else None,
                "open_": result["open"] if "open" in result else None,
                "volume": result["volume"] if "volume" in result else None,
            }
            parameters = inspect.signature(func).parameters
            accepted = {
                key: value
                for key, value in inputs.items()
                if key in parameters and value is not None
            }
            output = func(**accepted, **call_kwargs)
            if isinstance(output, pd.Series):
                result[output.name or f"{name}_{item}"] = output
            elif isinstance(output, pd.DataFrame):
                for column in output.columns:
                    result[column] = output[column]
            else:
                raise TypeError(f"pandas_ta indicator '{name}' returned unsupported output.")

        return result


ta = TAAccessor()


def list_indicators(pattern: str = "*") -> list[str]:
    """List public indicator names matching a shell-style pattern."""

    return sorted(name for name in _INDICATORS if fnmatch.fnmatch(name, pattern))


def indicator(name: str) -> Any:
    """Resolve an indicator by name."""

    if name.startswith("ta:"):
        return getattr(ta, name.split(":", 1)[1])
    if name in _INDICATORS:
        return IndicatorRunner(name)
    raise AttributeError(name)


def run_indicators(data: Any, selection: str = "native", period: Any = 20, **kwargs: Any) -> pd.DataFrame:
    """Run a group or pattern of indicators over data."""

    if selection in {"native", "smc"}:
        names = [name for name, group in _INDICATORS.items() if group == selection]
    else:
        names = list_indicators(selection)

    if not names:
        raise ValueError(f"No indicators matched selection: {selection}")

    result = _as_frame(data).copy()
    for name in names:
        item_period = "1D" if name == "phl" and not isinstance(period, str) else period
        result = IndicatorRunner(name).run(result, period=item_period, **kwargs)
    return result


class Indicator(ServiceNamespace):
    _service_module = "services.indicator"
    _service_modules = _SERVICE_MODULES


def __getattr__(name: str):
    if name in _PARAM_ALIASES:
        runner = IndicatorRunner(name)
        globals()[name] = runner
        return runner
    return resolve_service_attr(name, _SERVICE_MODULES)


__all__ = [
    "Indicator",
    "IndicatorRunner",
    "TAAccessor",
    "indicator",
    "list_indicators",
    "run_indicators",
    "ta",
    *_PARAM_ALIASES,
]


def _publish_package_exports() -> None:
    package = sys.modules.get(__package__)
    if package is None:
        return
    for name in __all__:
        if name in globals():
            setattr(package, name, globals()[name])


_publish_package_exports()
