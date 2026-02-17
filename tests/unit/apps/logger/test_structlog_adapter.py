from io import StringIO

from apps.utils.logger import StructlogAdapter
from apps.utils.redaction import REDACTED


def test_structlog_adapter_add_raw_callable_sink_receives_record():
    logger = StructlogAdapter(name="test.structlog")
    received = []

    sink_id = logger.add(received.append, level="INFO", raw=True)
    logger.info("hello")
    logger.remove(sink_id)

    assert received
    record = received[-1]
    assert record.message == "hello"
    assert record.level.name == "INFO"
    assert record.name == "test.structlog"
    assert record.file
    assert record.function
    assert isinstance(record.line, int)


def test_structlog_adapter_bind_and_redaction_with_stream_sink():
    logger = StructlogAdapter(name="test.structlog")
    stream = StringIO()

    sink_id = logger.add(stream, format="{message} | {extra}")
    bound = logger.bind(component="api")
    bound.info(
        "login failed password=supersecret token=abcd",
        extra={"api_key": "never-log-this", "safe": "ok"},
    )
    logger.remove(sink_id)

    output = stream.getvalue()
    assert "supersecret" not in output
    assert "abcd" not in output
    assert "never-log-this" not in output
    assert REDACTED in output
    assert "ok" in output
    assert "component" in output


def test_structlog_adapter_runtime_filter_by_severity():
    logger = StructlogAdapter(name="test.filter")
    received = []
    sink_id = logger.add(received.append, level="DEBUG", raw=True)

    logger.set_min_level("WARNING")
    logger.info("should be filtered")
    logger.warning("should pass")

    logger.remove(sink_id)
    logger.set_min_level("TRACE")

    assert len(received) == 1
    assert received[0].message == "should pass"
    assert received[0].level.name == "WARNING"


def test_structlog_adapter_runtime_filter_by_component():
    logger = StructlogAdapter(name="test.filter")
    received = []
    sink_id = logger.add(received.append, level="DEBUG", raw=True)

    logger.set_min_level("DEBUG")
    logger.set_component_level("risk", "ERROR")

    logger.info("risk info filtered", component="risk")
    logger.error("risk error pass", component="risk")
    logger.info("other info pass", component="other")

    logger.remove(sink_id)
    logger.clear_all_component_levels()

    assert [r.message for r in received] == ["risk error pass", "other info pass"]


def test_structlog_adapter_flush_calls_sink_flush():
    logger = StructlogAdapter(name="test.flush")

    class _Sink:
        def __init__(self) -> None:
            self.flushed = 0

        def write(self, _: str) -> None:
            return None

        def flush(self) -> None:
            self.flushed += 1

    sink = _Sink()
    sink_id = logger.add(sink)
    logger.info("hello")
    logger.flush()
    logger.remove(sink_id)

    assert sink.flushed >= 1

