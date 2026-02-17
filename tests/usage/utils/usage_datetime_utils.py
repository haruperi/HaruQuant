"""Usage examples for date/time and timezone normalization helpers."""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.utils.datetime_utils import (
    normalize_timestamp,
    normalize_timezone_for_series,
    parse_datetime,
    to_naive_utc,
    to_utc,
)


def main() -> None:
    print("--- datetime_utils usage ---")

    dt1 = parse_datetime("2026-02-17T10:30:00Z")
    print("parse ISO Z:", dt1)

    dt2 = parse_datetime(1_771_336_800)
    print("parse epoch_s:", dt2)

    print("to_utc:", to_utc(dt1))
    print("to_naive_utc:", to_naive_utc(dt1))

    print("normalize iso:", normalize_timestamp("2026-02-17T10:30:00+00:00", output="iso"))
    print("normalize epoch_ms:", normalize_timestamp("2026-02-17T10:30:00Z", output="epoch_ms"))

    idx = pd.date_range("2026-02-17 10:00:00", periods=3, freq="h")
    idx_athens = normalize_timezone_for_series(idx, target_tz="Europe/Athens")
    print("index timezone normalized:", idx_athens)


if __name__ == "__main__":
    main()

