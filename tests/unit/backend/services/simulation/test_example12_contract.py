import ast
from pathlib import Path


def test_example_12_uses_clean_engine_run_contract():
    path = Path("backend/scripts/examples/trading/trade_example.py")
    tree = ast.parse(path.read_text())
    target = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "example_12_complete_backtests":
            target = node
            break

    assert target is not None
    calls = [
        getattr(call.func, "id", getattr(call.func, "attr", ""))
        for call in ast.walk(target)
        if isinstance(call, ast.Call)
    ]

    assert "build_symbol_ticks_for_backtest" not in calls
    assert "reset_sim_runtime_state" not in calls
    assert any(
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "run"
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "engine_instance"
        for call in ast.walk(target)
        if isinstance(call, ast.Call)
    )
