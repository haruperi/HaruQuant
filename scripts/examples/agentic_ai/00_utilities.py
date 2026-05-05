from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yaml

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

EXAMPLE_ROOT = Path(__file__).resolve().parent
CONTRACTS_ROOT = Path(PROJECT_ROOT) / "backend_retiring" / "contracts"
WORKFLOW_DEFINITIONS_ROOT = Path(PROJECT_ROOT) / "backend_retiring" / "orchestration" / "workflow" / "definitions"
EXAMPLE_DATA_DIR = Path(PROJECT_ROOT) / "backend_retiring" / "data" / "market_data"
EXAMPLE_DATA_DIR.mkdir(parents=True, exist_ok=True)


def print_header(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_kv(label: str, value: Any, indent: int = 2) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        print(f"{prefix}{label}")
        for key, item in value.items():
            print(f"{prefix}  {key:<28s} {item}")
    elif isinstance(value, list):
        print(f"{prefix}{label}")
        for item in value:
            print(f"{prefix}  - {item}")
    else:
        print(f"{prefix}{label:<30s} {value}")


def load_workflow_definition(name: str) -> dict[str, Any]:
    path = WORKFLOW_DEFINITIONS_ROOT / f"{name}.yaml"
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"workflow definition {name!r} did not load as a mapping")
    return payload


def load_contract_example(contract_name: str, sample_name: str) -> dict[str, Any]:
    path = CONTRACTS_ROOT / contract_name / "examples" / "valid" / f"{sample_name}.json"
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"contract example {contract_name}/{sample_name} did not load as a mapping")
    return payload


def summarize_contract(payload: dict[str, Any]) -> dict[str, Any]:
    body = payload.get("payload", {})
    return {
        "contract_type": payload.get("contract_type"),
        "schema_version": payload.get("schema_version"),
        "environment": payload.get("environment"),
        "originator": payload.get("originator", {}).get("id"),
        "payload_keys": sorted(body.keys()),
    }


def summarize_workflow(definition: dict[str, Any]) -> list[str]:
    summary: list[str] = []
    for step in definition.get("steps", []):
        depends_on = ", ".join(step.get("depends_on", [])) or "none"
        summary.append(
            f"{step['name']}: agent={step['agent']}, output={step['expected_output']}, depends_on={depends_on}"
        )
    return summary


def _build_sample_ohlcv(n_bars: int = 200) -> pd.DataFrame:
    closes = [1.1000 + i * 0.0003 + (0.0005 if i % 7 == 0 else 0.0) for i in range(n_bars)]
    index = pd.date_range("2025-01-02", periods=n_bars, freq="h", tz="UTC")
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 0.0010 for c in closes],
            "low": [c - 0.0010 for c in closes],
            "close": closes,
            "volume": [100 + i * 2 for i in range(n_bars)],
        },
        index=index,
    )


def _ensure_sample_csv() -> Path:
    path = EXAMPLE_DATA_DIR / "eurusd_sample.csv"
    if not path.exists():
        frame = _build_sample_ohlcv()
        frame.reset_index().rename(columns={"index": "timestamp"}).to_csv(path, index=False)
    return path


def _ensure_sample_parquet() -> Path:
    path = EXAMPLE_DATA_DIR / "eurusd_sample.parquet"
    if not path.exists():
        _build_sample_ohlcv().to_parquet(path)
    return path


def _load_market_data(
    symbol: str = "EURUSD",
    timeframe: str = "H1",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    lookback_days: int = 14,
) -> Optional[pd.DataFrame]:
    from haruquant.data import load_mt5

    if start_date is None:
        end_date = end_date or datetime.now()
        start_date = end_date - timedelta(days=lookback_days)

    frame = load_mt5(
        symbol=symbol,
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
    )
    return frame if frame is not None and not frame.empty else None


def _redacted_env_status(key: str) -> str:
    env_path = Path(PROJECT_ROOT) / "backend_retiring" / "config" / "environments" / ".env"
    value = os.environ.get(key)
    if value is None and env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            env_key, _, env_value = line.partition("=")
            if env_key.strip() == key:
                value = env_value.strip().strip('"').strip("'")
                break
    if not value:
        return "missing"
    if len(value) <= 4:
        return "set"
    return f"set ({value[:2]}***{value[-2:]})"


def example_01_load_mt5() -> None:
    print_header("Example 01: Load Market Data - MT5")
    from haruquant.data import load_mt5, load_dukascopy

    symbol = "XAUUSD"
    timeframe = "H1"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    print_kv("Source", "MetaTrader 5 with Dukascopy fallback")
    print_kv("Symbol", symbol)
    print_kv("Timeframe", timeframe)
    print_kv("Date range", f"{start_date.date()} -> {end_date.date()}")
    print()

    try:
        frame = load_mt5(symbol=symbol, timeframe=timeframe, start_date=start_date, end_date=end_date)
        if frame is None:
            frame = load_dukascopy(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d"),
            )
        print("  OK loaded market data")
        print_kv("Rows", len(frame))
        print_kv("Columns", list(frame.columns))
        print(frame.head(5).to_string())
    except Exception as exc:
        print(f"  FAILED: {exc}")


def example_02_load_dukascopy() -> None:
    print_header("Example 02: Load Market Data - Dukascopy")
    from haruquant.data import load_dukascopy

    try:
        frame = load_dukascopy(symbol="EURUSD", timeframe="H1", start_date="2025-06-01", end_date="2025-06-08")
        print("  OK loaded market data")
        print_kv("Rows", len(frame))
        print(frame.head(5).to_string())
    except Exception as exc:
        print(f"  FAILED: {exc}")


def example_03_load_parquet() -> None:
    print_header("Example 03: Load Market Data - Parquet")
    from haruquant.data import load_parquet

    path = _ensure_sample_parquet()
    try:
        frame = load_parquet(path)
        print("  OK loaded parquet sample")
        print_kv("File", str(path))
        print_kv("Rows", len(frame))
        print(frame.head(5).to_string())
    except Exception as exc:
        print(f"  FAILED: {exc}")


def example_04_load_csv() -> None:
    print_header("Example 04: Load Market Data - CSVDataSource")
    from haruquant.data import CSVDataSource

    path = _ensure_sample_csv()
    try:
        source = CSVDataSource(path)
        frame = source.fetch_data(symbol="EURUSD", timeframe="H1", start_pos=0, end_pos=50)
        if frame is None:
            print("  FAILED: no data returned")
            return
        print("  OK loaded csv sample")
        print_kv("File", str(path))
        print_kv("Rows", len(frame))
        print(frame.head(5).to_string())
    except Exception as exc:
        print(f"  FAILED: {exc}")


def example_05_data_preprocess() -> None:
    print_header("Example 05: HaruQuant Dataset Pipeline")
    from haruquant.utils import normalize_columns, prepare_ohlcvs_dataset

    raw_frame = _load_market_data(symbol="EURUSD", timeframe="H1")
    if raw_frame is None:
        print("  FAILED: no market data returned from MT5 loader")
        return

    class InMemoryDataSource:
        def __init__(self, frame: pd.DataFrame) -> None:
            self._frame = frame

        def fetch_data(self, symbol: str, timeframe: str, start_pos: int, end_pos: int) -> Optional[pd.DataFrame]:
            if start_pos < 0 or end_pos > len(self._frame) or start_pos >= end_pos:
                return None
            return self._frame.iloc[start_pos:end_pos].copy()

    normalized = normalize_columns(raw_frame)
    dataset = prepare_ohlcvs_dataset(
        source=InMemoryDataSource(normalized),
        symbol="EURUSD",
        timeframe="H1",
        start_pos=0,
        end_pos=min(500, len(normalized)),
    )

    print("  OK prepared research dataset")
    print_kv("Rows", len(dataset.data))
    print_kv("Columns", list(dataset.data.columns))
    print_kv("Warnings", len(dataset.report.warnings))
    print_kv("Fatal errors", len(dataset.report.fatal_errors))


def example_06_env_healthcheck() -> None:
    print_header("Example 06: Environment Health Check")

    required = [
        "ENVIRONMENT",
        "API_HOST",
        "API_PORT",
        "HARUQUANT_AGENT_MODEL",
        "HARUQUANT_FAST_MODEL",
        "MT5_ENABLED",
        "MT5_LOGIN",
        "MT5_PASSWORD",
        "MT5_SERVER",
        "OPENAI_API_KEY",
        "JWT_SECRET_KEY",
        "DATA_ENCRYPTION_KEY",
    ]
    for key in required:
        print_kv(key, _redacted_env_status(key))


def example_07_contract_samples() -> None:
    print_header("Example 07: HaruQuant Contract Samples")
    samples = [
        ("trade_hypothesis", "eurusd_buy"),
        ("trade_proposal", "eurusd_ready_for_risk"),
        ("risk_assessment_decision", "approve_with_limits"),
        ("evaluation_report", "workflow_pass"),
        ("execution_receipt", "filled_limit_order"),
    ]
    for contract_name, sample_name in samples:
        summary = summarize_contract(load_contract_example(contract_name, sample_name))
        print_kv(f"{contract_name}/{sample_name}", summary)


def example_08_workflow_definitions() -> None:
    print_header("Example 08: HaruQuant Workflow Definitions")
    for workflow_name in ("proposal", "momentum_trading"):
        definition = load_workflow_definition(workflow_name)
        print_kv("Workflow", workflow_name)
        print_kv("Pattern", definition.get("pattern"))
        print_kv("Steps", summarize_workflow(definition))
        print()


if __name__ == "__main__":
    example_06_env_healthcheck()
    example_07_contract_samples()
    example_08_workflow_definitions()
