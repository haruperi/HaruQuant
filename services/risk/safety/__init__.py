"""Compatibility namespace for governance safety controls."""

from __future__ import annotations

_EXPORT_MODULES = {
    "KillSwitchBlockEvaluation": "kill_switch",
    "KillSwitchAction": "kill_switch",
    "KillSwitchService": "kill_switch",
    "KillSwitchStateMachine": "kill_switch",
    "KillSwitchTransitionError": "kill_switch",
    "RecoveryApproval": "kill_switch",
    "RecoveryAuthorization": "kill_switch",
    "evaluate_new_entry_block": "kill_switch",
    "require_hard_trigger_recovery_dual_auth": "kill_switch",
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str):
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value
