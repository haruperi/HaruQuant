"""Batch + streaming feature pipeline built on top of indicator modules (IP-13)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping

import pandas as pd

from backend.services.indicators.momentum.rsi import rsi as compute_rsi
from backend.services.indicators.trend.ema import ema as compute_ema
from backend.services.indicators.trend.sma import sma as compute_sma
from backend.services.indicators.trend.wma import wma as compute_wma
from backend.services.indicators.volatility.atr import atr as compute_atr
from backend.services.indicators.volatility.bbands import bbands as compute_bbands
from backend.services.indicators.volume.accumulation_distribution import (
    accumulation_distribution as compute_adl,
)


@dataclass(frozen=True)
class FeatureSpec:
    """One feature in the pipeline."""

    name: str
    params: Dict[str, Any] = field(default_factory=dict)


class FeaturePipeline:
    """Versioned feature pipeline supporting batch and incremental modes."""

    def __init__(
        self,
        features: Iterable[FeatureSpec],
        *,
        pipeline_version: str = "1.0.0",
        max_buffer_bars: int = 2000,
    ) -> None:
        self._features: List[FeatureSpec] = list(features)
        self.pipeline_version = pipeline_version
        self.max_buffer_bars = int(max_buffer_bars)
        self._buffers: Dict[str, pd.DataFrame] = {}

    def describe(self) -> Dict[str, Any]:
        """Return pipeline metadata for run manifests/inspection."""
        payload = {
            "pipeline_version": self.pipeline_version,
            "max_buffer_bars": self.max_buffer_bars,
            "features": [asdict(spec) for spec in self._features],
        }
        payload["pipeline_fingerprint"] = self.fingerprint()
        return payload

    def fingerprint(self) -> str:
        """Return a deterministic sha256 fingerprint for this pipeline definition."""
        payload = {
            "pipeline_version": self.pipeline_version,
            "max_buffer_bars": self.max_buffer_bars,
            "features": [asdict(spec) for spec in self._features],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return f"sha256:{hashlib.sha256(encoded.encode('utf-8')).hexdigest()}"

    def compute_batch(self, data: pd.DataFrame) -> pd.DataFrame:
        """Compute all configured features on a batch DataFrame."""
        result = data.copy()
        for spec in self._features:
            result = self._apply_feature(result, spec)
        result.attrs["feature_provenance"] = self._build_provenance(data)
        return result

    def compute_incremental(
        self,
        *,
        symbol: str,
        bar: Mapping[str, Any],
    ) -> Dict[str, Any]:
        """
        Update streaming buffer for one symbol and compute latest feature row.

        Expected bar keys:
        - timestamp
        - open, high, low, close, volume
        """
        ts = self._normalize_timestamp(bar.get("timestamp"))
        row = pd.DataFrame(
            [
                {
                    "open": float(bar["open"]),
                    "high": float(bar["high"]),
                    "low": float(bar["low"]),
                    "close": float(bar["close"]),
                    "volume": float(bar.get("volume", 0.0)),
                }
            ],
            index=pd.DatetimeIndex([ts], name="timestamp"),
        )

        existing = self._buffers.get(symbol)
        if existing is None or existing.empty:
            merged = row
        else:
            merged = pd.concat([existing, row], axis=0)
            merged = merged[~merged.index.duplicated(keep="last")]
            merged = merged.sort_index()

        if len(merged) > self.max_buffer_bars:
            merged = merged.iloc[-self.max_buffer_bars :]

        self._buffers[symbol] = merged
        enriched = self.compute_batch(merged)
        latest = enriched.iloc[-1].to_dict()
        latest["timestamp"] = enriched.index[-1]
        latest["symbol"] = symbol
        latest["feature_provenance"] = self._build_provenance(merged)
        latest["feature_pipeline_fingerprint"] = self.fingerprint()
        return latest

    def inspect_graph(self) -> Dict[str, Any]:
        """Return inspectable feature dependency graph."""
        nodes: List[str] = []
        edges: List[Dict[str, str]] = []

        for spec in self._features:
            out_cols = self._feature_output_columns(spec)
            deps = self._feature_dependencies(spec)
            for col in out_cols:
                nodes.append(col)
                for dep in deps:
                    edges.append({"from": dep, "to": col})

        return {"pipeline_version": self.pipeline_version, "nodes": nodes, "edges": edges}

    def _apply_feature(self, data: pd.DataFrame, spec: FeatureSpec) -> pd.DataFrame:
        name = spec.name.lower().strip()
        p = dict(spec.params)

        if name == "sma":
            return compute_sma(
                data,
                window=int(p.get("window", 20)),
                price_col=str(p.get("price_col", "close")),
            )
        if name == "ema":
            return compute_ema(
                data,
                span=int(p.get("span", 20)),
                price_col=str(p.get("price_col", "close")),
                adjust=bool(p.get("adjust", False)),
            )
        if name == "wma":
            return compute_wma(
                data,
                window=int(p.get("window", 20)),
                price_col=str(p.get("price_col", "close")),
            )
        if name == "rsi":
            return compute_rsi(
                data,
                period=int(p.get("period", 14)),
                price_col=str(p.get("price_col", "close")),
            )
        if name == "atr":
            return compute_atr(data, period=int(p.get("period", 14)))
        if name == "bbands":
            return compute_bbands(
                data,
                period=int(p.get("period", 20)),
                std_dev=float(p.get("std_dev", 2.0)),
                price_col=str(p.get("price_col", "close")),
            )
        if name in {"adl", "accumulation_distribution"}:
            return compute_adl(data)

        raise ValueError(f"unsupported feature: {spec.name}")

    def _build_provenance(self, source: pd.DataFrame) -> Dict[str, Any]:
        index = source.index if isinstance(source.index, pd.DatetimeIndex) else None
        return {
            "pipeline_version": self.pipeline_version,
            "pipeline_fingerprint": self.fingerprint(),
            "features": [asdict(spec) for spec in self._features],
            "source_rows": int(len(source)),
            "source_columns": [str(col) for col in source.columns],
            "source_start": index.min().isoformat() if index is not None and len(index) else None,
            "source_end": index.max().isoformat() if index is not None and len(index) else None,
        }

    @staticmethod
    def _normalize_timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    @staticmethod
    def _feature_dependencies(spec: FeatureSpec) -> List[str]:
        name = spec.name.lower().strip()
        price_col = str(spec.params.get("price_col", "close"))
        if name in {"sma", "ema", "wma", "rsi"}:
            return [price_col]
        if name == "atr":
            return ["high", "low", "close"]
        if name == "bbands":
            return [price_col]
        if name in {"adl", "accumulation_distribution"}:
            return ["high", "low", "close", "volume"]
        return []

    @staticmethod
    def _feature_output_columns(spec: FeatureSpec) -> List[str]:
        name = spec.name.lower().strip()
        p = spec.params
        if name == "sma":
            return [f"sma_{int(p.get('window', 20))}"]
        if name == "ema":
            return [f"ema_{int(p.get('span', 20))}"]
        if name == "wma":
            return [f"wma_{int(p.get('window', 20))}"]
        if name == "rsi":
            return [f"rsi_{int(p.get('period', 14))}"]
        if name == "atr":
            return [f"atr_{int(p.get('period', 14))}"]
        if name == "bbands":
            period = int(p.get("period", 20))
            std = float(p.get("std_dev", 2.0))
            suffix = f"{period}_{int(std) if std == int(std) else std}"
            return [f"bb_upper_{suffix}", f"bb_middle_{suffix}", f"bb_lower_{suffix}"]
        if name in {"adl", "accumulation_distribution"}:
            return ["adl"]
        return []
