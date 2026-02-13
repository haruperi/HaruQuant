"""Pure-Python tests for the backend selector (no C++ dependency)."""

from __future__ import annotations

import os
from unittest import mock

import pytest

from apps.simulation.backend import SimBackend, get_backend, is_cpp_available


# ---------------------------------------------------------------------------
# SimBackend enum
# ---------------------------------------------------------------------------


class TestSimBackend:
    def test_enum_values(self):
        assert SimBackend.PYTHON.value == "python"
        assert SimBackend.CPP.value == "cpp"

    def test_construction_from_string(self):
        assert SimBackend("python") is SimBackend.PYTHON
        assert SimBackend("cpp") is SimBackend.CPP

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError):
            SimBackend("unknown")


# ---------------------------------------------------------------------------
# get_backend()
# ---------------------------------------------------------------------------


class TestGetBackend:
    def test_default_is_python(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SIM_ENGINE", None)
            assert get_backend() is SimBackend.PYTHON

    def test_explicit_python(self):
        with mock.patch.dict(os.environ, {"SIM_ENGINE": "python"}):
            assert get_backend() is SimBackend.PYTHON

    def test_explicit_cpp(self):
        with mock.patch.dict(os.environ, {"SIM_ENGINE": "cpp"}):
            assert get_backend() is SimBackend.CPP

    def test_case_insensitive(self):
        with mock.patch.dict(os.environ, {"SIM_ENGINE": "CPP"}):
            assert get_backend() is SimBackend.CPP
        with mock.patch.dict(os.environ, {"SIM_ENGINE": "Python"}):
            assert get_backend() is SimBackend.PYTHON

    def test_whitespace_trimmed(self):
        with mock.patch.dict(os.environ, {"SIM_ENGINE": "  cpp  "}):
            assert get_backend() is SimBackend.CPP

    def test_unknown_falls_back_to_python(self):
        with mock.patch.dict(os.environ, {"SIM_ENGINE": "java"}):
            with pytest.warns(UserWarning, match="Unknown SIM_ENGINE"):
                assert get_backend() is SimBackend.PYTHON

    def test_empty_string_returns_python(self):
        with mock.patch.dict(os.environ, {"SIM_ENGINE": ""}):
            assert get_backend() is SimBackend.PYTHON


# ---------------------------------------------------------------------------
# is_cpp_available()
# ---------------------------------------------------------------------------


class TestIsCppAvailable:
    def test_returns_bool(self):
        result = is_cpp_available()
        assert isinstance(result, bool)
