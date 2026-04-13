# OMS State Machine and Idempotency (IP-31)

## Scope

This usage note covers:

- canonical order state transitions (`NEW -> ACCEPTED -> terminal`)
- idempotent submissions through `client_order_id`

Implementation is in C++ (`haruquant.sim`), used for both backtest and live-path integration.

## State Machine

`TradeSimulator.order_state_name(order_ticket)` returns:

- `NEW`
- `ACCEPTED`
- `PARTIALLY_FILLED`
- `FILLED`
- `CANCELED`
- `EXPIRED`
- `REJECTED`
- `UNKNOWN`

## Idempotent Submission

For submit actions (`DEAL`, `PENDING`):

- first request with a `client_order_id` is processed normally
- repeating same `client_order_id` with same payload returns cached first result
- repeating same `client_order_id` with different payload is rejected

## Example

See:

- `tests/usage/trade/oms_state_machine_idempotency_cpp.py`

## Test Evidence

- `cpp/tests/test_sim_oms_state_machine.cpp`


