from haruquant.risk import (
    PolicyBundle,
    PolicyResolutionQuery,
    PolicyResolver,
    PolicyScope,
    PolicyVersion,
)


def test_policy_resolver_prefers_most_specific_scope_match() -> None:
    base = PolicyBundle(
        scope=PolicyScope(environment="paper"),
        policies=(
            PolicyVersion(
                policy_version_id="policy_base",
                policy_type="risk",
                version="1.0.0",
                status="ACTIVE",
                effective_from="2026-04-09T00:00:00Z",
            ),
        ),
        bundle_version="bundle_base",
    )
    symbol_specific = PolicyBundle(
        scope=PolicyScope(environment="paper", symbol="EURUSD", role="TRADER"),
        policies=(
            PolicyVersion(
                policy_version_id="policy_symbol",
                policy_type="risk",
                version="1.1.0",
                status="ACTIVE",
                effective_from="2026-04-09T00:00:00Z",
            ),
        ),
        bundle_version="bundle_symbol",
    )
    resolver = PolicyResolver((base, symbol_specific))

    resolved = resolver.resolve(
        PolicyResolutionQuery(
            environment="paper",
            symbol="EURUSD",
            role="TRADER",
        )
    )

    assert resolved is not None
    assert resolved.bundle_version == "bundle_symbol"


def test_policy_resolver_returns_none_when_scope_does_not_match() -> None:
    resolver = PolicyResolver(
        (
            PolicyBundle(
                scope=PolicyScope(environment="paper", symbol="EURUSD"),
                policies=(),
                bundle_version="bundle_symbol",
            ),
        )
    )

    resolved = resolver.resolve(
        PolicyResolutionQuery(
            environment="prod",
            symbol="EURUSD",
        )
    )

    assert resolved is None
