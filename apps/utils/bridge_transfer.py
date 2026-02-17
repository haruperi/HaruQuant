"""Bridge transfer helpers: zero-copy fast path with serialization fallback."""

from __future__ import annotations

from typing import Any, Literal

import numpy as np


SerializationMode = Literal["auto", "arrow", "protobuf"]


def _as_1d_float64(values: Any) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("expected 1D numeric input")
    return np.ascontiguousarray(arr, dtype=np.float64)


def _sum_via_arrow(arr: np.ndarray) -> tuple[float, str]:
    try:
        import pyarrow as pa  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("pyarrow is not installed") from exc

    # Explicit serialization path for incompatible/cross-process style transfers.
    payload = pa.BufferOutputStream()
    with pa.ipc.new_stream(payload, pa.schema([("v", pa.float64())])) as writer:
        batch = pa.record_batch([pa.array(arr, type=pa.float64())], names=["v"])
        writer.write_batch(batch)
    buf = payload.getvalue()
    with pa.ipc.open_stream(buf) as reader:
        table = reader.read_all()
    decoded = np.asarray(table.column("v").to_numpy(), dtype=np.float64)

    import hqt_engine

    return float(hqt_engine.sum_buffer_zero_copy(decoded)), "arrow_fallback"


def _sum_via_protobuf(arr: np.ndarray) -> tuple[float, str]:
    try:
        from google.protobuf.struct_pb2 import ListValue  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("protobuf is not installed") from exc

    src = ListValue()
    src.extend([float(v) for v in arr])
    blob = src.SerializeToString()
    decoded_msg = ListValue()
    decoded_msg.ParseFromString(blob)
    decoded = np.asarray(list(decoded_msg), dtype=np.float64)

    import hqt_engine

    return float(hqt_engine.sum_buffer_zero_copy(decoded)), "protobuf_fallback"


def sum_with_fallback(values: Any, serialization: SerializationMode = "auto") -> dict[str, Any]:
    """Sum values through bridge transfer strategy.

    - ``auto``: C++ bridge decides zero-copy or copy fallback.
    - ``arrow``: explicit Arrow IPC roundtrip fallback path.
    - ``protobuf``: explicit Protobuf roundtrip fallback path.
    """
    import hqt_engine

    mode = str(serialization).lower()
    if mode == "auto":
        payload = hqt_engine.sum_auto(values)
        return {"total": float(payload["total"]), "path": str(payload["path"])}

    arr = _as_1d_float64(values)
    if mode == "arrow":
        total, path = _sum_via_arrow(arr)
        return {"total": total, "path": path}
    if mode == "protobuf":
        total, path = _sum_via_protobuf(arr)
        return {"total": total, "path": path}

    raise ValueError("serialization must be one of: auto, arrow, protobuf")

