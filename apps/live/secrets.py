"""Secret-provider helpers for live configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


class SecretProviderError(Exception):
    """Raised when a secret cannot be resolved from configured providers."""


@dataclass(frozen=True)
class SecretReference:
    provider: str
    service: str
    account: str


def parse_secret_reference(value: str) -> Optional[SecretReference]:
    """
    Parse secret references of format:
      keyring://<service>/<account>
    """
    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None
    if not text.lower().startswith("keyring://"):
        return None

    payload = text[len("keyring://") :]
    service, account = _split_service_account(payload)
    return SecretReference(provider="keyring", service=service, account=account)


def resolve_secret_reference(value: str) -> str:
    ref = parse_secret_reference(value)
    if ref is None:
        return value
    return get_secret(ref.provider, ref.service, ref.account)


def get_secret(provider: str, service: str, account: str) -> str:
    provider_name = str(provider).strip().lower()
    if provider_name != "keyring":
        raise SecretProviderError(f"Unsupported secret provider: {provider}")

    try:
        import keyring  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency-specific
        raise SecretProviderError(
            "keyring package is required for keyring:// secret references"
        ) from exc

    secret = keyring.get_password(service, account)
    if secret is None:
        raise SecretProviderError(
            f"Secret not found in keyring for service='{service}' account='{account}'"
        )
    return str(secret)


def _split_service_account(payload: str) -> Tuple[str, str]:
    parts = [p for p in payload.split("/") if p]
    if len(parts) < 2:
        raise SecretProviderError(
            "Invalid keyring secret reference. Expected keyring://<service>/<account>"
        )
    service = parts[0].strip()
    account = "/".join(parts[1:]).strip()
    if not service or not account:
        raise SecretProviderError(
            "Invalid keyring secret reference. Service/account cannot be empty"
        )
    return service, account

