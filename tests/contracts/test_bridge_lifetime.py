"""Contract tests for bridge ownership and lifetime safety (IP-19)."""

from __future__ import annotations

import gc
import sys
from pathlib import Path

import pytest

_build_dir = Path(__file__).resolve().parents[2] / "build" / "bridge" / "Release"
if _build_dir.exists():
    sys.path.insert(0, str(_build_dir))
sys.modules.pop("hqt_engine", None)

try:
    import hqt_engine
    from hqt_engine import sim

    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CPP_AVAILABLE, reason="C++ engine not built")


def test_ownership_contracts_api_shape() -> None:
    payload = hqt_engine.ownership_contracts()
    assert isinstance(payload, dict)
    assert payload["version"] == "1.0"
    assert "cpp_owned_python_view" in payload
    assert "shared_ownership" in payload
    assert "callback_rules" in payload
    assert "zero_copy" in payload


def test_zero_copy_sum_accepts_contiguous_float64() -> None:
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        pytest.skip("numpy not installed")

    arr = np.array([1.0, 2.5, 3.5], dtype=np.float64)
    out = hqt_engine.sum_buffer_zero_copy(arr)
    assert out == pytest.approx(7.0)


def test_zero_copy_sum_rejects_noncontiguous_or_wrong_dtype() -> None:
    try:
        import numpy as np
    except ImportError:  # pragma: no cover
        pytest.skip("numpy not installed")

    wrong_dtype = np.array([1, 2, 3], dtype=np.int32)
    with pytest.raises(TypeError):
        hqt_engine.sum_buffer_zero_copy(wrong_dtype)

    base = np.arange(10, dtype=np.float64)
    non_contiguous = base[::2]
    with pytest.raises(TypeError):
        hqt_engine.sum_buffer_zero_copy(non_contiguous)


def test_keep_alive_lifetime_for_engine_client_relationship() -> None:
    client = sim.SimulatorClient()
    engine = sim.BacktestEngine(client)

    # Drop Python reference to client; keep_alive/shared ownership contract should keep it valid.
    del client
    gc.collect()

    state = engine.state()
    assert state is not None
