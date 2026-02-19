import os
import sys
import time
import logging
import threading
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, NonCallableMagicMock
from datetime import datetime, timezone, timedelta

import apps.utils.logger as logger_mod
from apps.utils.logger import (
    StructlogAdapter,
    CompatRecord,
    _SizeAndTimeRotatingFileSink,
    _CompatLevel,
    _SinkEntry,
    _Core,
    _is_access_record,
    _configure_default_file_sinks,
    _configure_structlog,
    _LEVELS
)

@pytest.fixture
def temp_log_dir(tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir

class TestSizeAndTimeRotatingFileSink:
    def test_init_creates_dir(self, temp_log_dir):
        path = temp_log_dir / "test.log"
        sink = _SizeAndTimeRotatingFileSink(path, max_bytes=100, backup_count=2)
        assert path.exists()
        sink.close()

    def test_write_and_flush(self, temp_log_dir):
        path = temp_log_dir / "test.log"
        sink = _SizeAndTimeRotatingFileSink(path, max_bytes=100, backup_count=2)
        sink.write("hello")
        sink.flush()
        assert path.read_text() == "hello"
        sink.close()

    def test_rotation_by_size(self, temp_log_dir):
        path = temp_log_dir / "test.log"
        sink = _SizeAndTimeRotatingFileSink(path, max_bytes=10, backup_count=2)
        sink.write("12345678901")
        backups = list(temp_log_dir.glob("test.log.*"))
        assert len(backups) == 1
        sink.close()

    def test_rotation_by_time(self, temp_log_dir):
        path = temp_log_dir / "test.log"
        sink = _SizeAndTimeRotatingFileSink(path, max_bytes=1000, backup_count=2)
        future_time = sink._next_day_rollover + 1
        with patch("time.time", return_value=future_time):
            sink.write("rotate")
        backups = list(temp_log_dir.glob("test.log.*"))
        assert len(backups) == 1
        sink.close()

    def test_prune_old_backups_error(self, temp_log_dir):
        path = temp_log_dir / "test_prune.log"
        sink = _SizeAndTimeRotatingFileSink(path, max_bytes=2, backup_count=0)
        sink.write("123")
        sink.write("456")
        mock_file = MagicMock(spec=Path)
        mock_file.is_file.return_value = True
        mock_file.name = "test_prune.log.2024"
        mock_file.stat.return_value.st_mtime = time.time()
        mock_file.unlink.side_effect = Exception("fail")
        with patch.object(Path, "iterdir", return_value=[mock_file]):
            sink._prune_old_backups()
        sink.close()

    def test_rotate_collisions_and_path_exists(self, temp_log_dir):
        # Hit line 149 (path.exists() in _rotate)
        path = temp_log_dir / "collision.log"
        sink = _SizeAndTimeRotatingFileSink(path, max_bytes=5, backup_count=5)
        sink.write("first")
        # Now it exists. Next write will trigger rotate.
        sink.write("second_trigger_rotate")
        sink.close()

    def test_rotate_path_not_exists(self, temp_log_dir):
        # Hit line 149 branch False
        path = temp_log_dir / "none.log"
        sink = _SizeAndTimeRotatingFileSink(path, max_bytes=5, backup_count=5)
        # Manually delete before rotate
        if path.exists(): path.unlink()
        sink._rotate()
        sink.close()

class TestStructlogAdapter:
    @pytest.fixture
    def adapter(self):
        return StructlogAdapter(name="test_logger", core=_Core())

    def test_init_no_structlog(self):
        with patch("apps.utils.logger._HAS_STRUCTLOG", False):
            with patch("logging.getLogger") as m:
                a = StructlogAdapter(name="test_no_sl")
                m.assert_called_with("test_no_sl")

    def test_add_remove_sink(self, adapter, temp_log_dir):
        log_file = temp_log_dir / "add_test.log"
        sid = adapter.add(log_file)
        assert sid in adapter._core.sinks
        adapter.remove(sid)
        assert sid not in adapter._core.sinks

    def test_add_path_str(self, adapter, temp_log_dir):
        # Hit line 238 isinstance(sink, (str, Path))
        adapter.add(str(temp_log_dir / "str_path.log"))

    def test_add_isatty(self, adapter):
        m = MagicMock()
        m.isatty.return_value = True
        adapter.add(m)
        assert adapter._core.sinks[adapter._core.next_id - 1].colorize == True

    def test_remove_all_sinks(self, adapter):
        adapter.add(sys.stdout)
        adapter.remove()
        assert len(adapter._core.sinks) == 0

    def test_remove_with_error(self, adapter):
        mock_sink = MagicMock()
        mock_sink.close.side_effect = Exception("fail")
        sid = adapter.add(mock_sink)
        adapter._core.sinks[sid].close_on_remove = True
        adapter.remove(sid)

    def test_set_min_level(self, adapter):
        adapter.set_min_level("DEBUG")
        assert adapter.get_min_level() == "DEBUG"

    def test_component_levels(self, adapter):
        adapter.set_component_level("c1", "DEBUG")
        adapter.clear_component_level("c1")
        adapter.clear_all_component_levels()
        assert len(adapter._core.component_levels) == 0

    def test_flush_with_error_and_no_flush(self, adapter):
        m1 = MagicMock()
        m1.flush.side_effect = Exception("fail")
        adapter.add(m1)
        # Hit line 309->307: sink WITHOUT flush
        m2 = NonCallableMagicMock() # No flush
        adapter.add(m2)
        adapter.flush()

    def test_bind_contextualize(self, adapter):
        with adapter.contextualize(a=1) as a:
            assert a._bound_extra["a"] == 1

    def test_emit_logic(self, adapter):
        m = MagicMock()
        adapter.add(m, level="INFO", raw=True)
        adapter.debug("no")
        m.assert_not_called()
        adapter.info("yes")
        m.assert_called()

    def test_emit_structlog_variants(self, adapter):
        with patch("apps.utils.logger._HAS_STRUCTLOG", True):
            adapter._logger = MagicMock()
            m = MagicMock()
            adapter.add(m, raw=True, level="TRACE")
            adapter.error("msg", exc_info=True) 
            adapter.warning("msg")
            adapter.debug("msg")
            adapter.info("msg") 
            
        with patch("apps.utils.logger._HAS_STRUCTLOG", False):
            adapter._logger = MagicMock()
            adapter.error("msg", exc_info=True)
            adapter.warning("msg")
            adapter.debug("msg")
            adapter.info("msg")

    def test_shorthand_methods(self, adapter):
        m = MagicMock()
        adapter.add(m, level="TRACE", raw=True)
        adapter.trace("t")
        adapter.success("s") # Hit line 332
        adapter.exception("ex") # Hit line 344-345
        adapter.critical("c")

    def test_log_method_pathways(self, adapter):
        m = MagicMock()
        adapter.add(m, raw=True, level="DEBUG")
        adapter.log("DEBUG", "msg") # Normalized string
        adapter.log(10, "msg") # Int (Line 349-350)
        adapter.log(20, "msg") # Int (Line 349-350)
        adapter.log(100, "msg") # Unknown Int (Line 351 normalized)
        assert m.call_count == 4

    def test_emit_should_log_false(self, adapter):
        # Hit line 368
        m = MagicMock()
        adapter.add(m, level="ERROR", raw=True)
        adapter.debug("wont_be_emitted")
        m.assert_not_called()

    def test_emit_exception_block(self, adapter):
        # Hit line 420-422
        with patch("apps.utils.logger.redact_mapping", side_effect=Exception("fail")):
            adapter.info("msg")

    def test_dispatch_pathways(self, adapter):
        # Case 1: Not Callable, has write, No flush (line 449->429)
        m4 = MagicMock(spec=["write"])
        with patch("apps.utils.logger.callable", return_value=False):
            adapter.add(m4, raw=False)
            adapter.info("msg")
            
        # Case 2: Not Callable, NO write (line 445->429)
        adapter.remove()
        m5 = MagicMock(spec=[])
        with patch("apps.utils.logger.callable", return_value=False):
            adapter.add(m5, raw=False)
            adapter.info("msg")

    def test_dispatch_filter_exception(self, adapter):
        # Hit line 436-437
        m = MagicMock()
        adapter.add(m, filter=lambda r: 1/0, raw=True)
        adapter.info("msg") 

    def test_dispatch_sink_exception(self, adapter):
        # Hit line 451-453
        m = MagicMock()
        m.side_effect = Exception("fail")
        adapter.add(m, raw=True)
        adapter.info("msg")

    def test_format_record_fail(self, adapter):
        r = CompatRecord(datetime.now(), _CompatLevel("INFO", 20), "m", "n", "f", "fu", 1, "", "", "")
        assert "m" in adapter._format_record(r, "{nonexistent}") # Line 487 fallback

    def test_colorize_unk(self, adapter):
        # Hit line 503
        assert adapter._colorize_level("UNK_LVL") == "UNK_LVL"

    def test_caller_meta_depth_break(self):
        # Hit line 512 (frame is None -> break)
        assert StructlogAdapter._caller_meta(depth=1000)["file"] == "<unknown>" # Line 515

    def test_caller_meta_exception(self):
        # Hit line 521-522
        with patch("inspect.currentframe", side_effect=Exception("f")):
            assert StructlogAdapter._caller_meta()["file"] == "<unknown>"

    def test_conf_structlog_reentry(self):
        # Hit line 186 (double-checked lock)
        with patch("apps.utils.logger._STRUCTLOG_CONFIGURED", False):
            mock_lock = MagicMock()
            def side_effect(*args, **kwargs):
                logger_mod._STRUCTLOG_CONFIGURED = True
            mock_lock.__enter__.side_effect = side_effect
            with patch("apps.utils.logger._CONFIG_LOCK", mock_lock):
                 _configure_structlog()

    def test_conf_def_sinks_idemp(self):
        # Hit line 571
        with patch("apps.utils.logger._DEFAULT_FILE_SINKS_CONFIGURED", True):
            with patch("apps.utils.logger.Path") as mp:
                _configure_default_file_sinks()
                mp.assert_not_called()

def test_is_acc_rec():
    r = MagicMock(spec=CompatRecord)
    r.extra = {"component": "access"}
    assert _is_access_record(r) == True
    r.extra = {"method": "GET"}
    assert _is_access_record(r) == True

@pytest.mark.parametrize("l,e", [
    ("warn", "WARNING"), (123, "CRITICAL"), (5, "TRACE"), (8, "DEBUG"), (25, "SUCCESS"), 
    (logging.INFO, "INFO"), (logging.WARNING, "WARNING"), (logging.ERROR, "ERROR"), (logging.DEBUG, "DEBUG"),
    (28, "WARNING"), (45, "CRITICAL") # Hit line 533->exit, 535->exit variants
])
def test_norm_lvl(l, e):
    assert StructlogAdapter._normalize_level_name(l) == e
