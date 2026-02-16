from apps.utils.redaction import REDACTED, redact_mapping, redact_text


def test_redact_mapping_masks_sensitive_keys():
    payload = {
        "username": "alice",
        "password": "secret123",
        "nested": {"api_key": "abcd"},
        "token_value": "keep-out",
    }
    redacted = redact_mapping(payload)

    assert redacted["username"] == "alice"
    assert redacted["password"] == REDACTED
    assert redacted["nested"]["api_key"] == REDACTED
    assert redacted["token_value"] == REDACTED


def test_redact_text_masks_common_patterns():
    text = 'password=abc123 token:xyz Bearer jwt_token {"api_key":"mykey"}'
    out = redact_text(text)
    assert "abc123" not in out
    assert "xyz" not in out
    assert "jwt_token" not in out
    assert "mykey" not in out
    assert REDACTED in out
