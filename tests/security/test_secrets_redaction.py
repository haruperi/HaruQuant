from io import StringIO

from apps.logger.logger import Logger
from apps.utils.redaction import REDACTED


def test_logger_redacts_secret_message_and_extra():
    sink = StringIO()
    test_logger = Logger()
    test_logger.add(sink, format="{message} | {extra}")

    test_logger.info(
        "login failed password=supersecret token=abcd",
        extra={"api_key": "never-log-this", "safe": "ok"},
    )

    output = sink.getvalue()
    assert "supersecret" not in output
    assert "abcd" not in output
    assert "never-log-this" not in output
    assert REDACTED in output
    assert "ok" in output
